"""One bounded attribution probe: cold pools and sparse warm tile costs.

No field is created. Process-local wrappers time whole existing calls and return
their results unchanged. No solver, routing, scheduling or persistence edit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
import subprocess
from time import perf_counter

import numpy as np

from ....src.generation import runner
from ....src.generation.work_units import ScalarCellTask
from ....src.lyapunov import field_adapter, operational, hybrid, s1
from ....src.lyapunov.reference import RenormalizedTangentSpec


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PERFORMANCE_DIRECTORY / "evidence" / "current" / "s1_remaining_costs.json"

ACTIVE = None
COLD = {}


def timed(original, label):
    def wrapper(*args, **kwargs):
        if ACTIVE is None:
            return original(*args, **kwargs)
        started=perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            ACTIVE[label]=ACTIVE.get(label,0.0)+perf_counter()-started
    return wrapper


def initialize(spec):
    global ACTIVE, COLD
    for module,name,label in (
        (operational,'evaluate_renormalized_tangent_s1','s1_attempt'),
        (hybrid,'evaluate_renormalized_tangent_compiled_dop853','trusted_attempt'),
        (hybrid,'_verify_endpoint_max_step_incompatibility','verification'),
        (hybrid,'evaluate_renormalized_tangent_compiled','solve_ivp_fallback'),
        (s1,'_native_callbacks','callbacks'),
        (s1,'native_library','native_build_load'),
    ):
        setattr(module,name,timed(getattr(module,name),label))
    ACTIVE={}
    started=perf_counter()
    field_adapter.initialize_lyapunov_field_worker(spec)
    COLD=dict(seconds=perf_counter()-started,phases=dict(ACTIVE))
    ACTIVE=None


def measure(task):
    global ACTIVE
    ACTIVE={}
    start=perf_counter()
    try:
        outcome=runner._evaluate_bound_cell(task)
        end=perf_counter()
        phases=dict(ACTIVE)
    finally:
        ACTIVE=None
    # callbacks/native_build_load are nested in s1_attempt, not additive.
    return outcome,dict(start=start,end=end,phases=phases,cold=COLD)


def tasks_for_tile(row,col):
    axis=np.linspace(-np.pi,np.pi,128,endpoint=False)
    return tuple(ScalarCellTask(i*128+j,i,j,float(axis[i]),float(axis[j]))
        for i in range(row*8,row*8+8) for j in range(col*8,col*8+8))


def identity(outcome):
    e=outcome.evaluation
    return (outcome.task,e.status,e.value,e.diagnostics,e.evaluator,
            e.attempted_evaluators,e.recovery_reason,e.implementation_provenance,e.attempt_provenance)


def run_horizon(horizon):
    spec=RenormalizedTangentSpec(duration=horizon)
    binding=replace(field_adapter.lyapunov_evaluator_binding(spec),initialize_worker=initialize)
    execution=runner.accepted_process_execution_spec()
    pool,identities,setup=runner._open_pool(binding,execution)
    tiles=[]; workers={}; controls=[]
    try:
        for row in (0,5,10,15):
            for col in (0,5,10,15):
                tasks=tasks_for_tile(row,col)
                started=perf_counter()
                returned=tuple(pool.map(measure,tasks,chunksize=execution.chunksize))
                wall=perf_counter()-started
                records=[]
                for outcome,detail in returned:
                    workers[outcome.worker_pid]=detail.pop('cold')
                    e=outcome.evaluation
                    records.append(dict(index=outcome.task.linear_index,pid=outcome.worker_pid,
                        route=e.evaluator,status=e.status.value,recovery=e.recovery_reason,
                        value=e.value,nfev=e.diagnostics.solver_function_evaluations,
                        peak_rss=outcome.worker_peak_rss_bytes,**detail))
                span=max(r['end'] for r in records)-min(r['start'] for r in records)
                busy=sum(r['end']-r['start'] for r in records)
                per_worker=defaultdict(float)
                for r in records:per_worker[r['pid']]+=r['end']-r['start']
                tiles.append(dict(tile=[row,col],wall=wall,worker_span=span,
                    busy_seconds=busy,max_worker_busy=max(per_worker.values()),records=records))
        # Paired same-pool control on two selected tiles; the timing wrappers
        # bypass measurement for production calls. This tests numerical identity
        # and reports instrumentation effects rather than correcting timings.
        for row,col in ((5,5),(0,0)):
            for reverse in (False,True):
                results={};times={}
                for label,fn in ((('instrumented',measure),('plain',runner._evaluate_bound_cell))
                                 if not reverse else (('plain',runner._evaluate_bound_cell),('instrumented',measure))):
                    started=perf_counter(); result=tuple(pool.map(fn,tasks_for_tile(row,col),chunksize=1))
                    times[label]=perf_counter()-started
                    results[label]=tuple(identity(r[0] if label=='instrumented' else r) for r in result)
                controls.append(dict(tile=[row,col],reverse=reverse,seconds=times,
                    exact_results=results['plain']==results['instrumented']))
    finally:
        shutdown,stopped=runner._close_pool(pool,identities)
    records=[r for t in tiles for r in t['records']]
    groups={}
    for route in sorted({r['route'] for r in records}):
        group=[r for r in records if r['route']==route]
        groups[route]=dict(cells=len(group),mean_worker_seconds=mean(r['end']-r['start'] for r in group),
            phase_mean_seconds={key:mean(r['phases'].get(key,0.0) for r in group)
                for key in ('s1_attempt','trusted_attempt','verification','solve_ivp_fallback')})
    wall=sum(t['wall'] for t in tiles)
    return dict(horizon=horizon,setup=setup,shutdown=shutdown,stopped=stopped,
        worker_identities=[asdict(i) for i in identities],workers=workers,
        routes=groups,tiles=tiles,controls=controls,
        total_tile_wall=wall,total_worker_busy=sum(t['busy_seconds'] for t in tiles),
        summed_worker_span=sum(t['worker_span'] for t in tiles),
        summed_max_worker_busy=sum(t['max_worker_busy'] for t in tiles),
        occupancy=sum(t['busy_seconds'] for t in tiles)/(4*wall),
        all_valid=all(r['status']=='completed_valid' for r in records),
        all_controls_exact=all(c['exact_results'] for c in controls))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    if args.output.exists():parser.error('Evidence exists; choose a new output path.')
    data=dict(question='Separate per-pool cold initialization, successful S1 work, recovery/fallback and tile waiting.',
        design='16 sparse 8x8 tiles on the 128-axis at block indices 0,5,10,15; two horizons; four spawn workers; no HDF5.',
        cells_per_pool=1536,attributed_cells_per_horizon=1024,
        environment=s1.s1_build_provenance(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),horizons=[])
    for horizon in (5.0,20.0):
        result=run_horizon(horizon);data['horizons'].append(result)
        print(json.dumps({key:result[key] for key in ('horizon','setup','shutdown','routes','total_tile_wall','occupancy','all_valid','all_controls_exact','stopped')},indent=2),flush=True)
    args.output.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
