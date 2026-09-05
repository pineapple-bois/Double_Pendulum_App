"""Deterministic bounded validation of the promoted S1 implementation."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
from statistics import median
import subprocess
from time import perf_counter
import warnings

import numba
import numpy as np
import scipy

from ....src.lyapunov.s1 import (
    S1_BUILD_FLAGS as BUILD_FLAGS,
    S1_NATIVE_DIRECTORY,
    evaluate_renormalized_tangent_s1 as evaluate_compiled_loop,
    run_renormalized_tangent_s1 as run_compiled_loop,
)
from ....src.lyapunov import s1 as promoted_s1_module
from ....src.lyapunov.compiled_dop853 import (
    run_renormalized_tangent_compiled_dop853 as trusted_run,
    evaluate_renormalized_tangent_compiled_dop853 as trusted_evaluate,
)
from ....src.lyapunov.hybrid import evaluate_renormalized_tangent_hybrid
from ....src.lyapunov.compiled_equivalence import (
    compare_results, VALIDATION_ANGLE_PAIRS_DEGREES, RATE_ABSOLUTE_TOLERANCE,
    CYCLE_LOG_ABSOLUTE_TOLERANCE, FINAL_REFERENCE_DISTANCE_TOLERANCE,
    FINAL_TANGENT_DISTANCE_TOLERANCE, ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
)
from ....src.lyapunov.reference import (
    EulerLagrangeState, RenormalizedTangentSpec, SolverSpec, PendulumParameters,
)

DIRECTORY = Path(__file__).resolve().parent
EVIDENCE_DIRECTORY = DIRECTORY.parent / "evidence" / "s1"
HORIZONS = (1.0, 2.0, 5.0, 10.0, 20.0)


def radical_inverse(index, base):
    result, factor = 0.0, 1.0/base
    while index:
        index, digit = divmod(index, base)
        result += digit*factor
        factor /= base
    return result


def validation_cases():
    """Fixed before running S1; preserve duplicate states with distinct purposes."""
    cases = []

    def add(name, group, a, b, w1=0.0, w2=0.0, relation=None, **options):
        cases.append(dict(name=name, group=group, relation=relation,
            spec=RenormalizedTangentSpec(initial_state=EulerLagrangeState(a,b,w1,w2),**options)))

    recorded=json.loads((EVIDENCE_DIRECTORY/"route_stratified_16_cells.json").read_text())["cells"]
    for c in recorded:
        add(f"recorded_{c['theta2_index']}_{c['theta1_index']}",c["stratum"],
            c["theta1_radians"],c["theta2_radians"])
    angles=(-np.pi,-np.pi/2,0.0,np.pi/2,np.nextafter(np.pi,0.0))
    for i,a in enumerate(angles):
        for j,b in enumerate(angles):
            add(f"domain_{i}_{j}","domain_landmarks",a,b)
    for i in range(1,13):
        a,b=(2*np.pi*radical_inverse(i,base)-np.pi for base in (2,3))
        add(f"halton_{i}","domain_halton",a,b)
        add(f"reflection_{i}","reflection",-a,-b,
            initial_tangent=(-1.0,0.0,0.0,0.0),
            relation=dict(base=f"halton_{i}",kind="reflection"))
    for i,(a,b) in enumerate(((177.75,170.25),(176.5,170.25),
                             (181.5,170.66666666666666),(180.66666666666666,170.66666666666666))):
        add(f"audited_boundary_{i}","audited_boundary",float(np.deg2rad(a)),float(np.deg2rad(b)))
    for i,c in enumerate([c for c in recorded if c["stratum"]=="persisted_fallback"][:4]):
        for sign in (-1,1):
            add(f"neighbor_{i}_{sign}","route_neighbor",c["theta1_radians"]+sign*2*np.pi/1024,
                c["theta2_radians"])
    for i,(a,b) in enumerate(VALIDATION_ANGLE_PAIRS_DEGREES):
        add(f"oracle_fixture_{i}","existing_oracle",float(np.deg2rad(a)),float(np.deg2rad(b)))
    for c in (recorded[0],next(c for c in recorded if c["theta2_index"]==440)):
        name=f"recorded_{c['theta2_index']}_{c['theta1_index']}"
        for i,(l1,l2) in enumerate(((1,0),(0,-1),(10,-10))):
            add(f"lift_{name}_{i}","periodic_lift",c["theta1_radians"]+l1*2*np.pi,
                c["theta2_radians"]+l2*2*np.pi,relation=dict(base=name,kind="lift"))
    for i,a in enumerate((np.nextafter(-np.pi,-np.inf),np.nextafter(np.pi,np.inf),
                          -np.pi+1e-12,np.pi-1e-12)):
        add(f"seam_{i}","chart_seam",a,-0.7)
    for i,(a,b,w1,w2) in enumerate(((0.73,-1.21,2.4,-3.1),(2.7,-2.4,6.,-4.))):
        add(f"velocity_{i}","nonzero_velocity",a,b,w1,w2)
        add(f"velocity_reflection_{i}","nonzero_velocity",-a,-b,-w1,-w2,
            initial_tangent=(-1.,0.,0.,0.),relation=dict(base=f"velocity_{i}",kind="reflection"))
    for interval in (0.2,0.5,1.0):
        add(f"interval_{interval}","reset_policy",-2.79,-2.25,renormalization_interval=interval)
    cap=math.sqrt(1/9.81)/32
    for step in (0.005,0.01,float(np.nextafter(cap,np.inf))):
        add(f"cap_{step}","endpoint_policy",-2.79,-2.25,solver=SolverSpec(max_step=step))
    add("mixed_tangent","tangent_geometry",-2.79,-2.25,initial_tangent=(0.2,-0.3,0.4,0.1))
    add("nondefault_physics","physical_parameters",-0.5645,-0.4418,
        characteristic_length=1.7,parameters=PendulumParameters(1.3,0.7,1.2,0.9,9.4))
    assert len({c['name'] for c in cases})==len(cases)
    return cases


def observe(runner,spec):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result=runner(spec)
        except (RuntimeError,ValueError) as error:
            return None,dict(status="execution_error" if isinstance(error,RuntimeError) else "specification_error",
                error_type=type(error).__name__,error=str(error),warnings=[str(w.message) for w in caught])
    return result,dict(status="completed_valid" if result.diagnostics.numerically_valid else "completed_invalid",
        rate=result.finite_time_stretching_rate,diagnostics=asdict(result.diagnostics),
        final_reference=result.final_reference_state.tolist(),final_tangent=result.final_unit_tangent.tolist(),
        final_log_growth=float(result.cumulative_log_stretch[-1]),
        warnings=[str(w.message) for w in caught])


def compare(reference,candidate):
    result=compare_results(reference,candidate)
    for field in ("cumulative_log_stretch","stretch_factor"):
        result[field+"_maximum_absolute_error"]=float(np.max(np.abs(
            getattr(reference,field)-getattr(candidate,field))))
    result["norm_diagnostic_absolute_error"]=abs(
        reference.diagnostics.maximum_post_renormalization_norm_error-
        candidate.diagnostics.maximum_post_renormalization_norm_error)
    # Derived, not relaxed: each prefix's accumulated growth / end time is its
    # finite-time rate. Apply the existing rate gate at every cycle boundary.
    result["maximum_prefix_rate_error"]=float(np.max(np.abs(
        reference.cumulative_finite_time_rate-candidate.cumulative_finite_time_rate)))
    result["counts_match"]=(reference.diagnostics.segment_count==candidate.diagnostics.segment_count
        and reference.diagnostics.solver_function_evaluations==candidate.diagnostics.solver_function_evaluations)
    result["cycle_times_identical"]=bool(np.array_equal(reference.cycle_end_time,candidate.cycle_end_time))
    result["reset_norm_gate_matches"]=(
        (reference.diagnostics.maximum_post_renormalization_norm_error<=reference.spec.renormalization_norm_tolerance)
        ==(candidate.diagnostics.maximum_post_renormalization_norm_error<=candidate.spec.renormalization_norm_tolerance))
    result["bookkeeping_pass"]=all(
        np.all(np.isfinite(r.stretch_factor)) and np.all(r.stretch_factor>0)
        and np.max(np.abs(r.log_stretch_increment-np.log(r.stretch_factor)))<=2e-15
        and np.max(np.abs(r.cumulative_log_stretch-np.cumsum(r.log_stretch_increment)))<=2e-15
        and abs(r.finite_time_stretching_rate-r.cumulative_log_stretch[-1]/r.spec.duration)<=2e-15
        for r in (reference,candidate))
    result["accepted"]=bool(result["accepted"] and result["counts_match"] and
        result["cycle_times_identical"] and result["reset_norm_gate_matches"] and
        result["bookkeeping_pass"] and result["maximum_prefix_rate_error"]<=RATE_ABSOLUTE_TOLERANCE)
    return result


def check_case(spec,include_hybrid=True):
    reference,rs=observe(trusted_run,spec)
    candidate,cs=observe(run_compiled_loop,spec)
    row=dict(trusted_fast=rs,s1=cs)
    if reference is not None and candidate is not None:
        row["comparison"]=compare(reference,candidate)
        row["accepted"]=row["comparison"]["accepted"]
    else:
        row["accepted"]=bool(reference is candidate is None and rs["status"]==cs["status"]
            and rs["error_type"]==cs["error_type"])
        if "max_step" in rs.get("error","") or "max_step" in cs.get("error",""):
            row["accepted"] &= rs.get("error")==cs.get("error")
    if include_hybrid:
        operational=evaluate_renormalized_tangent_hybrid(spec)
        row["operational"]=dict(route=operational.evaluator,status=operational.status.value,
            rate=operational.value,error=operational.error_message,
            diagnostics=asdict(operational.diagnostics) if operational.diagnostics else None)
        if reference is not None:
            row["accepted"] &= (operational.evaluator=="compiled_dop853"
                and operational.status.value==rs["status"] and operational.value==rs["rate"])
        # A rejected S1 has no accepted scientific record to compare with a
        # solve_ivp fallback. Preserve that absence, rather than substituting one.
    return row


def run(repetitions):
    cases=validation_cases()
    rows=[]
    for horizon in HORIZONS:
        for c in cases:
            spec=replace(c["spec"],duration=horizon)
            rows.append(dict(name=c["name"],group=c["group"],horizon=horizon,
                spec=asdict(spec),**check_case(spec)))
        print(f"T={horizon:g}: {sum(r['accepted'] for r in rows if r['horizon']==horizon)}/{len(cases)} comparisons pass",flush=True)
    # Relations are descriptive: long-time roundoff can break exact equality of
    # physically related input lifts even in the trusted implementation.
    relations=[]
    lookup={(r['name'],r['horizon']):r for r in rows}
    for c in cases:
        if not c["relation"]: continue
        for horizon in HORIZONS:
            base=lookup[c["relation"]["base"],horizon]; related=lookup[c["name"],horizon]
            relations.append(dict(name=c["name"],horizon=horizon,**c["relation"],
                trusted_rate_difference=(related["trusted_fast"]["rate"]-base["trusted_fast"]["rate"])
                    if "rate" in related["trusted_fast"] and "rate" in base["trusted_fast"] else None,
                s1_rate_difference=(related["s1"]["rate"]-base["s1"]["rate"])
                    if "rate" in related["s1"] and "rate" in base["s1"] else None,
                trusted_routes=[base["operational"]["route"],related["operational"]["route"]]))
    # Prefix scans minimise up to three failing inputs. If all pass, trace three
    # fixed representative cases instead. Each run uses unchanged solver policy.
    failed_names=list(dict.fromkeys(r["name"] for r in rows if not r["accepted"]))[:3]
    trace_names=failed_names or ["recorded_145_57","recorded_294_27","recorded_440_420"]
    traces=[]
    for name in trace_names:
        c=next(c for c in cases if c["name"]==name)
        limit=min((r["horizon"] for r in rows if r["name"]==name and not r["accepted"]),default=20.)
        for cycle in range(1,int(round(limit/c["spec"].renormalization_interval))+1):
            spec=replace(c["spec"],duration=cycle*c["spec"].renormalization_interval)
            r=check_case(spec,include_hybrid=False)
            traces.append(dict(name=name,horizon=spec.duration,**r))
            if not r["accepted"]: break
    print(f"Prefix traces: {len(traces)}; failures {sum(not t['accepted'] for t in traces)}",flush=True)
    robustness=[]
    base=RenormalizedTangentSpec(duration=0.25)
    for name,spec in (
        ("energy_invalid",replace(base,energy_drift_limit=1e-20)),
        ("norm_invalid",replace(base,renormalization_norm_tolerance=1e-20)),
        ("step_budget",replace(base,solver=SolverSpec(max_step=1e-7))),
        ("wrong_solver",replace(base,solver=SolverSpec(method="RK45"))),
        ("nonfinite_input",replace(base,initial_state=EulerLagrangeState(float('nan'),0,0,0))),
    ):
        robustness.append(dict(name=name,**check_case(spec,include_hybrid=False)))
    # Mechanically pick up to 24 cells, round-robin across groups, requiring only
    # trusted completed-valid fast success at BOTH horizons. No speed/accuracy filter.
    eligible=[c for c in cases if all(lookup[c['name'],t]['trusted_fast']['status']=='completed_valid'
                                      for t in (5.,20.))]
    selected=[]
    groups=list(dict.fromkeys(c['group'] for c in cases))
    while eligible and len(selected)<24:
        for group in groups:
            found=next((c for c in eligible if c['group']==group),None)
            if found is not None and len(selected)<24:
                selected.append(found);eligible.remove(found)
    timing=[]
    for c in selected:
        for horizon in (5.,20.):
            spec=replace(c['spec'],duration=horizon)
            trusted_evaluate(spec);evaluate_compiled_loop(spec)
            timing.append(dict(name=c['name'],horizon=horizon,trusted_seconds=[],s1_seconds=[]))
    for rep in range(repetitions):
        for row in (timing if rep%2==0 else timing[::-1]):
            c=next(c for c in selected if c['name']==row['name'])
            spec=replace(c['spec'],duration=row['horizon'])
            funcs=[('trusted_seconds',trusted_evaluate),('s1_seconds',evaluate_compiled_loop)]
            for key,fn in (funcs if rep%2==0 else funcs[::-1]):
                start=perf_counter(); outcome=fn(spec); elapsed=perf_counter()-start
                if outcome.value is None: raise RuntimeError(f"Timing failure: {row['name']}")
                row[key].append(elapsed)
    for row in timing:
        row['trusted_median_seconds']=median(row['trusted_seconds'])
        row['s1_median_seconds']=median(row['s1_seconds'])
        row['speedup']=row['trusted_median_seconds']/row['s1_median_seconds']
    summary={str(t):dict(cases=sum(r['horizon']==t for r in rows),
        passed=sum(r['accepted'] for r in rows if r['horizon']==t),
        operational_routes=dict(Counter(r['operational']['route'] for r in rows if r['horizon']==t))) for t in HORIZONS}
    performance={str(t):dict(cells=sum(r['horizon']==t for r in timing),
        median_speedup=median(r['speedup'] for r in timing if r['horizon']==t),
        minimum_speedup=min(r['speedup'] for r in timing if r['horizon']==t)) for t in (5.,20.)}
    worst={}
    for key in ('absolute_rate_error_per_second','maximum_cycle_log_absolute_error',
        'final_reference_candidate_a_distance','final_tangent_candidate_a_distance',
        'energy_diagnostic_absolute_error','norm_diagnostic_absolute_error',
        'cumulative_log_stretch_maximum_absolute_error','maximum_prefix_rate_error'):
        r=max((r for r in rows+traces if 'comparison' in r),key=lambda r:r['comparison'][key])
        worst[key]=dict(value=r['comparison'][key],name=r['name'],horizon=r['horizon'])
    files=[Path(__file__),Path(promoted_s1_module.__file__),
           EVIDENCE_DIRECTORY/'route_stratified_16_cells.json',
           *sorted(S1_NATIVE_DIRECTORY.iterdir())]
    return dict(timestamp=datetime.now(timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
            numba=numba.__version__,platform=platform.platform(),flags=BUILD_FLAGS,
            compiler=subprocess.check_output(['clang','--version'],text=True).strip(),
            git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()),
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        gates=dict(rate=RATE_ABSOLUTE_TOLERANCE,cycle_log=CYCLE_LOG_ABSOLUTE_TOLERANCE,
            final_reference=FINAL_REFERENCE_DISTANCE_TOLERANCE,final_tangent=FINAL_TANGENT_DISTANCE_TOLERANCE,
            energy_diagnostic=ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
            prefix_rate=RATE_ABSOLUTE_TOLERANCE,bookkeeping=2e-15,
            counts_and_status='exact',energy_and_norm_limits='unchanged values from each spec'),
        cases=rows,summary=summary,worst=worst,relations=relations,prefix_traces=traces,
        robustness=robustness,timing=timing,performance=performance,repetitions=repetitions,
        all_validation_pass=all(r['accepted'] for r in rows+traces+robustness))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output',
        type=Path,
        default=EVIDENCE_DIRECTORY/'s1_promotion_validation.json',
    )
    parser.add_argument('--repetitions',type=int,default=7)
    args=parser.parse_args()
    if args.output.exists(): parser.error('Choose a new output path; evidence is not overwritten.')
    if args.repetitions<3: parser.error('At least three repetitions required.')
    data=run(args.repetitions)
    args.output.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:data[k] for k in ('summary','worst','performance','all_validation_pass')},indent=2))


if __name__=='__main__':
    main()
