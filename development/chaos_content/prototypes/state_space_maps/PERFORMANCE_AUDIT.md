# State-space maps: runtime and throughput audit

Audit date: 2026-09-04. Inspected checkout: `893fb7d9ea8c4faf25a9dca4f7aaac9fa5088bb7`.

This is a documentation-only investigation. No optimisation, configuration change, numerical run, benchmark, test run, or regeneration was performed. Timings below come from existing artifacts; calculations on those records are identified as derived evidence. Paths below are relative to this directory unless explicitly described as repository-relative.

## Principal findings

The operational Lyapunov path already has an explicit compiled flow/Jacobian-vector product and a compiled DOP853 integration driver. The next ceiling is in the surrounding execution: repeated worker lifecycles, thousands of Python/native RHS transitions per cell, accepted-step callbacks and allocations, segment construction, and whole-horizon fallback work. Recommending merely “use Numba” would miss the current implementation.

The strongest findings are:

1. **The 2,048-cell pool policy has already been implemented.** The earlier 1,024-cell policy spent 39.95% of its 1024² runner wall time in setup plus shutdown. The newer 512² T=5 artifact still spends 25.60% there. Reducing import/JIT costs and explaining worker retention offer material remaining gains; repeating the already-promoted policy change does not.
2. **N scaling is reasonably efficient within the evaluation phase.** The locally available 512², 1024² and 2048² T=5 artifacts have almost identical recorded solver work per cell and fallback fractions. Evaluation wall grows approximately with N², without a demonstrated resolution-dependent collapse. This does not establish total-run scaling: the 2048² whole-run manifest is absent.
3. **T scaling is less favourable.** At fixed N=512, T=20 costs 5.40 times the evaluation wall of T=5, for four times the horizon. Fallback rises from 4.26% to 11.50%. Maximum recorded worker peak RSS rises from about 318 to 627 MiB under the same cell-count recycling policy. These are observations, not proof of a specific leak or a complete causal timing model.
4. **There is a concrete non-default-duration validation defect.** The CLI generates with the requested duration but validates with the default T=5 spec. Resolve this in a separately authorised correctness change before trusting further horizon-sweep completion evidence. Nothing was fixed in this audit.
5. **HDF5 writes and IPC are lower-priority targets today.** Named persistence costs are about 1% of measured generation wall. The T=5 evaluator occupancy proxy is roughly 93–94%; that leaves limited apparent evaluation-phase headroom for scheduling alone. Repeated validation reads matter more for resume/render latency and future accelerated kernels than for current integration-dominated generation.
6. **The highest upside comes from doing fewer repeated integrations or moving the complete small-system loop into compiled code.** Multi-horizon execution, verified reuse of nested-grid cells, and compilation across the solver/callback boundary deserve staged experiments. They require more care than local allocation cleanup.

## Actual execution paths

### Periodic finite-time stretching field

The normal CLI path is:

```text
runners/generate_lyapunov_periodic_field.py::main
  -> RenormalizedTangentSpec(duration=arguments.duration)
  -> lyapunov/field_adapter.py::run_periodic_lyapunov_field
  -> generation/runner.py::run_scalar_field
       -> plan_tiles: row-major 8 x 8 rectangles
       -> create/compatibility checks, resume discovery
       -> four spawn workers; pool-wide 2,048 returned-cell lifetime
       -> tasks_for_work_unit: 64 indexed cell tasks
       -> executor.map(_evaluate_bound_cell, tasks, chunksize=1)
            -> specification_for_cell: dataclass replacement
            -> evaluate_renormalized_tangent_hybrid
                 -> compiled-DOP853 attempt
                 -> if eligible: full endpoint-verification replay
                 -> if verified: full compiled-RHS solve_ivp fallback
       -> _compact_tile: scalar arrays, statuses/routes, diagnostics
       -> write_completed_tile: coordinator-only HDF5 transaction
       -> repeat; close pool; repeated final validation/read passes
  -> validate_lyapunov_oracle_spots
  -> write_manifest, only if validation succeeds
```

The coordinator waits for an entire tile before compaction and persistence, then dispatches the next tile. Workers do not own whole tiles and do not write HDF5. There is no cross-tile queue keeping workers busy during coordinator work. Task/result retention is bounded to a tile, while the full tile plan and final field snapshots scale with N².

Each worker initialises through `initialize_lyapunov_field_worker`, evaluating the complete base spec once. The kernel in `lyapunov/compiled.py::compiled_reference_and_tangent_rhs` uses `@njit(cache=False)`. Each spawned interpreter therefore needs its own compilation; an already-warmed parent does not supply that compiled state to spawn children.

The shared `lyapunov/reference.py::_run_renormalized_tangent_with_rhs`:

- builds Candidate-A geometry, a diagonal matrix and its generic inverse, the initial unit tangent, initial energy, and cycle boundaries per evaluation;
- for each 0.25 s segment, constructs a requested-time array, concatenates the reference and tangent, constructs a new solver, integrates, normalises the tangent, rebases physical angles, evaluates energy diagnostics, and appends cycle histories;
- creates a full `RenormalizedTangentResult`, although `evaluation.py` ultimately retains only the final scalar and compact diagnostics for field generation.

The fast segment calls `scipy.integrate.ode(...).set_integrator("dop853")`. Its RHS path is **Fortran -> Python `counted_rhs` -> Python bound closure -> Numba dispatcher/kernel**, returning a newly allocated eight-element array. Its `solout` callback copies every accepted eight-component state into a Python list. After integration, it converts lists to arrays, validates finiteness/time ordering, and computes accepted-step gaps. There is no end-to-end compiled observable.

Defaults resolve `max_step = min(sqrt(1/9.81)/32, 0.25/25) = 0.009977357137720327 s`, with `rtol=1e-9`, `atol=1e-11`. T=5 has 20 segments and roughly 500-plus accepted steps per successful cell. The retained fast-route sample records 6,565 RHS evaluations per cell. A 1024² field consequently entails **20,971,520 base segment solves**, plus partial attempts/replays for fallback cells; T=20 would entail 83,886,080 base segments at that resolution. These are structural counts, not measured timings for such a T=20 field.

The compiled segment uses requested-time **endpoints**, not the interior uniform grid. Energy is checked on accepted steps. The `solve_ivp` reference/fallback uses `t_eval=requested` and checks energy on that uniform grid. Thus changing `sampling_interval` is neither a direct way to reduce fast-route steps nor a scientifically neutral way to accelerate fallback diagnostics.

### First-flip field

`runners/generate_first_flip_periodic_field.py::main` uses the same generation/persistence pipeline with `first_flip/field_adapter.py::first_flip_evaluator_binding`. Its worker initialiser builds cached `EulerLagrangeDynamics` once per parameter set per worker. `first_flip/reference.py::_cached_dynamics` already has an LRU cache of size 16.

`first_flip_time` integrates a continuous **four-state** physical trajectory through `solve_ivp`, with four signed terminal event functions. It uses the lambdified `EulerLagrangeDynamics.flow`, not the compiled eight-state tangent kernel. Observed flips stop early; censored cells integrate to the horizon. It retains accepted solver states until energy and maximum angular-increment diagnostics are calculated, constructs `FirstFlipResult`, then adapts that to smaller field diagnostics. No tangent integration, angular rebasing, renormalisation, or QR occurs here.

### Reference sampling, teaching, and rendering

`lyapunov/grid.py::run_theta1_theta2_grid` and `lyapunov/sweep.py::run_theta1_sweep` default to the symbolic/reference evaluator. They use serial `state_space_fields.py::sample_rectangle/sample_line`, retain per-cell objects, and rebuild arrays when `values/statuses/valid_mask` properties are accessed. These are small reference APIs, **not the high-resolution CLI path**.

`reference.py::run_sensitivity_to_lyapunov` computes finite-pair trajectories, tangent traces, positions and pedagogical comparisons. None of that position/finite-shadow rendering work occurs in the operational scalar evaluator. There is no full-spectrum QR hot path to optimise.

`runners/render_finite_time_field.py::render_persisted_field` validates and reads HDF5, builds a Matplotlib `imshow` figure, and saves PNG at 600 dpi plus PDF. It does not invoke science or workers. It also handles the first-flip cap overlay, despite older documentation saying no first-flip renderer exists. The source and tests are the current evidence for this path.

## Existing performance and provenance evidence

### Evidence boundaries

All nine local HDF5 artifacts were opened with `h5py.File(..., "r")`. Inspection covered definitions, tile states, timings, diagnostic JSON, all tile execution policies, status counts, chunk layout and sizes. Timing/statistic extraction did not run prototype evaluators or mutation-capable probes. This audit did **not** re-run the authoritative checksum validator or numerical oracle gates; “complete/valid” below means recorded tile/status evidence, supplemented by existing validation records where available.

All inspected field artifacts record Python 3.12.3, NumPy 2.5.2, SciPy 1.18.0, h5py 3.16.0, HDF5 2.0.0 and macOS 15.7.9 ARM64; Lyapunov artifacts also record Numba 0.67.0. Hardware load, thermal state, exact CPU allocation and run ordering are insufficiently recorded for controlled cross-artifact speedup claims.

The historical investigation README refers to a 1024 artifact at the former top-level output path and says no 2048 field exists. The current local artifact is under `002_1024_squared/`, and `003_2048_squared/` now exists. Preserve the historical account as dated evidence; do not let its earlier scope statements erase newer local evidence.

### T=5 resolution comparison

These are sums of persisted tile evaluation wall times, **excluding worker lifecycle, persistence and final validation**.

| Local HDF5 under `outputs/finite_time_field/` | Recorded Git prefix | Pool limit | Cells | Evaluation wall sum | Evaluation cells/s | Summed evaluator seconds | Recorded nfev/cell | Fallback | Occupancy proxy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `001_512_squared/finite_time_field_512.h5` | `c53cac7` | 1,024 | 262,144 | 728.497 s | 359.842 | 2,713.626 | 6,680.411 | 4.2580% | 93.12% |
| `002_1024_squared/finite_time_field_1024.h5` | `0c93940` | 1,024 | 1,048,576 | 2,855.321 s | 367.236 | 10,658.766 | 6,680.451 | 4.2411% | 93.32% |
| `003_2048_squared/finite_time_field_2048.h5` | `faefd78` | 2,048 | 4,194,304 | 10,895.149 s | 384.970 | 40,798.795 | 6,680.280 | 4.2257% | 93.62% |

All tiles have recorded COMPLETE state and all cell statuses are completed-valid. The 2048 artifact has 65,536 tiles and 177,238 fallback cells. Its evaluation sum is 3.026 hours; **this is not its total generation runtime**. No 2048 JSON whole-run/oracle manifest was found.

Evaluation scaling ratios are 3.919 and 3.816 for successive fourfold cell-count increases. This supports near-linear scaling in cell count for these T=5 workloads, not a claim that the policy change or higher resolution itself accelerated numerical integration.

Artifact sizes are 20,719,184 / 82,651,415 / 329,983,878 bytes. The three uncompressed field arrays need only 10 bytes/cell: 2.5 / 10 / 40 MiB respectively. Stored files are about 7.9 times those payload sizes despite compression, consistent with substantial small-chunk and per-tile metadata overhead. This is a storage observation, not evidence that write compression dominates runtime.

Occupancy here is `sum(evaluator elapsed)/(4 * sum(tile wall))`. It is not CPU utilisation. It combines timer boundaries, scheduling, IPC, imbalance, and host effects, and can change when implementation overhead moves across the evaluator boundary.

### Whole-run accounting: old and current pool limits

Sources: [1024 manifest](outputs/finite_time_field/002_1024_squared/finite_time_field_1024.json) and [512 T=5 manifest](outputs/finite_time_field/004_Tsweep/data/finite_time_field_512_T5.json).

| Recorded component | 1024², former 1,024-cell limit | 512² T=5, current 2,048-cell limit |
| --- | ---: | ---: |
| Runner wall | 4,958.228 s | 990.421 s |
| Operation through oracle validation | 4,968.435 s | 993.486 s |
| Pool setup | 1,553.887 s (31.34%) | 193.471 s (19.53%) |
| Tile evaluation | 2,855.321 s (57.59%) | 710.425 s (71.73%) |
| Tile persistence | 48.226 s (0.97%) | 11.626 s (1.17%) |
| Pool shutdown | 427.112 s (8.61%) | 60.086 s (6.07%) |
| Other runner time, derived by subtraction | 73.683 s (1.49%) | 14.813 s (1.50%) |
| Pools | 1,024 | 128 |
| End-to-end runner throughput | 211.482 cells/s | 264.679 cells/s |

Both manifests record successful oracle validation and all workers stopped. The first has 9 accepted spots. The second records the same default-horizon contract, with Git prefix `9dca046`.

`run_scalar_field` starts its total timer **after** creation/initial compatibility checking. Its evaluation timer covers dispatch/wait but excludes task construction and compaction. `_close_pool` records shutdown time before a further 20 ms sleep. Final validation and resume scans fall into total/unattributed time. CLI operation timing begins after its first definition construction and ends before manifest serialization/writing. These scopes explain why sums and outer timings are not interchangeable.

Derived upper bounds, holding all other work fixed: eliminating the current run's entire lifecycle bucket could save at most 25.60% of wall (about 1.34x throughput); eliminating all named persistence could save only 1.17%. Neither bound is an achievable forecast. The earlier 39.95% lifecycle share must not be quoted as the remaining opportunity under the current policy.

### Horizon sweep: a stronger warning than N alone

Source: `outputs/finite_time_field/004_Tsweep/data/finite_time_field_512_T{1,2,5,10,20}.h5`. These all record Git `9dca046`, 4,096 complete tiles, four workers, a 2,048-cell pool limit, and 262,144 completed-valid cells.

| T | Segments/cell | Tile evaluation wall | Mean evaluator ms/cell | Fallback fraction | Recorded nfev/cell/T | Largest recorded worker peak RSS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 s | 4 | 137.361 s | 1.863 | 2.2896% | 1,342.95 | 244.23 MiB |
| 2 s | 8 | 263.831 s | 3.712 | 2.6657% | 1,325.97 | 262.14 MiB |
| 5 s | 20 | 710.425 s | 10.097 | 4.2580% | 1,336.08 | 317.69 MiB |
| 10 s | 40 | 1,589.277 s | 22.561 | 6.7505% | 1,345.07 | 418.98 MiB |
| 20 s | 80 | 3,832.809 s | 54.711 | 11.4971% | 1,359.41 | 627.14 MiB |

Only T=5 has a JSON completion manifest. The duration mismatch described below is consistent with absent non-default manifests, but no terminal log proves why those particular sidecars are absent. Completed HDF5 statuses alone do not establish horizon-correct oracle acceptance.

The nearly constant **retained** nfev per cell per simulated second does not account for all work: `summarize_lyapunov_tile` sums the final returned diagnostics, omitting discarded fast attempts and verification replays. Hybrid elapsed time includes those phases. T=20 has 5.40x the T=5 tile wall and 5.42x its summed evaluator time, while retained nfev grows 4.07x. Increasing fallback is a plausible contributor supported by the route structure; these records cannot quantitatively isolate it from other effects.

The RSS values are maxima across worker lifetime high-water marks, not simultaneous aggregate current RSS. They demonstrate that a 2,048-cell policy is not a fixed memory envelope across T. They do not justify multiplying a T=5 leak-rate estimate indefinitely or selecting a larger pool limit.

### Bounded probes already available

- [Performance investigation](investigations/performance/README.md): neutral spawn/handshake setup averaged 0.227 s versus 1.424 s for accepted Lyapunov workers; shutdown 0.029 versus 0.346 s. Maximum accepted worker warm-up averaged 0.339 s. Imports, JIT and interpreter cleanup were not individually isolated.
- [Route-stratified 16 cells](investigations/performance/route_stratified_16_cells.json): eight fast cells averaged 6.433 ms; eight fallback cells 45.164 ms. Fallback comprised 2.763 ms failed attempt, 6.561 ms verification replay and 35.825 ms `solve_ivp`. All matched stored values/statuses/routes. This is a tiny sequential warmed sample, not a population or multiprocessing profile.
- [Worker lifetime](investigations/performance/worker_lifetime_4096_cells.json): median current RSS rose from 221.59 MiB ready to 264.12 at 1,024, 306.16 at 2,048 and 392.65 at 4,096 pool-wide cells. Throughput did not show a monotonic collapse. The README's 0.1666 MiB per individual cell fit is descriptive, not a leak diagnosis. A bounded 4,096-cell observation exists; a validated 4,096-cell **policy** does not.
- [Fast-only A/B](investigations/performance/worker_lifetime_ab_2048_cells.json): 2,048 reuse reduced mean active wall about 21.04%, with about 42 MiB extra endpoint RSS per worker. Its approximately 4.91% evaluation-throughput penalty did not reproduce consistently in the mixed-route runner study.
- [Runner A/B](investigations/performance/runner_recycling_candidate_64.json) and [preregistered design](investigations/performance/runner_recycling_candidate_design.json): three paired 64² runs, 3,886 fast/210 fallback cells, adjusted wall 21.125 -> 16.917 s (19.88% mean paired saving), about 170 MiB additional aggregate worker RSS. Scientific equality, create/resume, integrity and worker termination were retained. This is the evidence behind the already-promoted default.
- [Earlier RHS compilation assessment](outputs/lyapunov/reference_vs_compiled_equivalence.json): reference median 0.361729 s versus compiled-RHS/`solve_ivp` 0.038296 s, 9.45x on six warmed evaluations per path; cold compiled call 0.353636 s. The reference timing includes repeated dynamics construction. This is neither an isolated RHS microbenchmark nor a further 9.45x gain available on the current hybrid path.
- [First-flip pilot](outputs/first_flip_pilot/first_flip_field_32_T5s.json): 1,024 cells, 450 events/574 censored, 4,945,310 RHS calls, 13.192 s tile evaluation, 3.855 s setup, 0.349 s shutdown, 0.042 s writes, 17.526 s runner wall, 20.143 s operation, and 9 accepted stricter spots. Median-of-tile-medians integration time is 54.8 ms; it is not the median of all cell end-to-end times.

Historical probe code needs review before reuse. In particular `probe_runner_recycling_candidate.py::_policies` takes today's accepted policy and replaces its limit with 2,048, then asserts a difference: now both limits are 2,048, so this old A/B no longer defines two policies. Some historical paths also predate artifact relocation. None of these probes was executed here; some write evidence even in design modes.

## Ranking of opportunities

Impact labels describe plausible scope-specific gains, not measured promises. Confidence concerns the opportunity; causal uncertainty is stated separately. Implementation risk includes operational and maintenance complexity. Numerical changes must receive new scientific acceptance, even if they produce faster or visually similar fields.

| Priority | ID | Category and proposal | Likely qualitative speedup | Confidence | Implementation risk |
| --- | --- | --- | --- | --- | --- |
| Prerequisite | L0 | Pass the actual horizon to oracle validation; reject mismatched specs early | Small kernel effect; prevents failed completion/repeated work | High | Low |
| 1 | L1 | Reduce import/JIT/warm-up repetition within the existing pool policy | Moderate | High for cost centre; medium for individual fixes | Low–medium |
| 2 | A1 | Explain retained worker memory, then reconsider bounded lifetime accounting | Large if it unlocks reuse | Medium; low for a particular root cause | Medium |
| 3 | L2 | Hoist fixed geometry, grids and preparation out of cell loops | Small–moderate | High for repetition; medium for wall impact | Low–medium |
| 4 | L3 | Scalar-only accumulation and lean accepted-step handling | Moderate | Medium | Medium |
| 5 | S1 | Compile solver/RHS/diagnostics together across callback boundaries | Potentially transformative for warm compute | Medium for opportunity; low for achievable factor | High |
| 6 | A2 | Reuse integration across requested horizons | Large for sweeps | High for duplicate work; medium for equivalence | High |
| 7 | N1 | Reduce fallback through a separately validated endpoint/solver treatment | Moderate at T=5; potentially large at longer T | Medium | High |
| 8 | L4 | First-flip flow-only preparation and compiled four-state RHS | Large for that consumer, no current Lyapunov-field gain | Medium–high | Medium |
| 9 | A3 | Small task batches, bounded cross-tile scheduling and worker-width study | Small now; moderate after faster kernels | Medium | Medium |
| 10 | L5/A4 | Consolidate integrity passes and improve storage access organisation | Small generation gain; moderate read/resume gain | High for repetition; medium for timing | Medium |
| 11 | N2 | Relax/tune step cap, tolerances, diagnostic sampling or reset interval | Potentially large if science permits | Low–medium | Medium–high |
| 12 | A5 | Reuse exact shared cells of nested grids | Moderate for repeated resolution escalation | High for work saving; medium for transfer contract | Medium–high |
| 13 | S2 | Batched CPU/GPU, reflection symmetry, or adaptive spatial sampling | Potentially transformative in suitable workloads | Low overall | High |

## 1. Low-risk implementation improvements

### L0 — Make validation use the generated specification

**Location:** `runners/generate_lyapunov_periodic_field.py::main` (oracle call near line 294); `src/lyapunov/field_adapter.py::validate_lyapunov_oracle_spots`; `tests/test_operational_runners.py`.

**Current work and expense:** `main` constructs `specification` from `--duration` and supplies it to generation, but calls `validate_lyapunov_oracle_spots(output_path)` without it. The validator silently constructs `RenormalizedTangentSpec()` at T=5. It then compares the persisted non-default-horizon scalar to a different calculation and can return failure after the expensive field has completed. It does not first check that the supplied spec agrees with persisted numerical metadata. First-flip's main correctly passes its spec and its spot validator explicitly checks the stored horizon.

**Proposal:** in a future correctness change, pass the exact specification and check its relevant physical/numerical fields against artifact metadata before any oracle integration. Keep completion failure explicit and distinguish completed HDF5 work from missing final oracle acceptance; do not regenerate dynamics just to recover a sidecar. Consider recording phase/failure evidence even when final acceptance fails, without labelling it success.

**Assessment:** small direct speedup; high confidence; low implementation risk. Scientific risk is low if the comparison is simply corrected, but existing non-default-horizon artifacts still require their actual gates and must not be retroactively declared accepted. Validate with a stubbed CLI argument-propagation test and tiny real T=1/T=10 create/resume checks; prove deliberate metadata mismatch fails before oracle work. Existing tests do not exercise this non-default-duration CLI handoff. No fix or revalidation was performed here.

### L1 — Reduce cold-worker cost without increasing the lifetime limit

**Locations:** `src/lyapunov/compiled.py::compiled_reference_and_tangent_rhs`; `src/lyapunov/field_adapter.py::initialize_lyapunov_field_worker`; `src/lyapunov/reference.py` imports; `src/lyapunov/__init__.py`; `src/generation/runner.py::_open_pool/_wait_for_workers/_close_pool`.

**Current work and expense:** fresh workers compile the uncached kernel and evaluate the complete requested horizon for warm-up. Imports of scientific types bring in SymPy and the production Lagrangian module, which eagerly imports Matplotlib/Plotly. Eager package exports also load reference, sampling and adapter modules. The compiled field needs the parameter/type definitions but not a symbolic derivation or plotting implementation on each worker's normal path. At 1024² under the current limit, a full create would need 512 pool lifetimes and 2,048 worker initialisations; at 2048², 2,048 pools and 8,192 initialisations, assuming full tiles and no interruptions.

**Proposal:** separately evaluate an explicit writable Numba cache with clear invalidation/versioning, a lighter worker import graph (lazy reference-only imports or separated type definitions), and a bounded warm-up that compiles the actual signature plus checks an appropriate short valid case. Preserve a meaningful initializer failure check. JIT cache loading will still have cost; warm-up changes must not silently remove long-horizon support checks that callers rely on. The 20 ms identity/close sleeps are secondary; replace polling with a reliable readiness protocol only if measured worthwhile.

**Assessment:** moderate end-to-end gain; high confidence that lifecycle is material, medium confidence about the split. Low–medium implementation risk; low scientific risk for unchanged kernels, with cache invalidation, parameter capture and import cycles the main concerns. Benchmark cold-cache and warm-cache spawn pools separately, timing imports, compilation, warm evaluation and teardown. Repeat T=1/5/20 and mixed routes under the unchanged 2,048 limit. Require exact scientific output/status/route preservation, cache-miss recovery, no stale code and verified worker termination. Do not attribute the entire setup bucket to LLVM.

### L2 — Prepare invariant numerical data once per worker/spec

**Locations:** `src/lyapunov/reference.py::_run_renormalized_tangent_with_rhs`, `CandidateAMetric`, `_energy_scale`, `_resolved_interval_max_step`; `src/lyapunov/field_adapter.py::specification_for_cell/initialize_lyapunov_field_worker`; `src/generation/runner.py::_compact_tile`; `src/generation/work_units.py::tasks_for_work_unit`.

**Current work and expense:** each cell revalidates the fixed tangent/spec through `replace`, recalculates the same metric and inverse, builds the same boundaries and segment sample grids, binds an RHS closure, and recalculates fixed energy scale. Fallback replay repeats preparation. Compaction constructs the same expected task dataclasses a second time and reconstructs route/status dictionaries per tile. There are millions of cells and tens of millions of segments, even though a single construction is cheap.

**Proposal:** make an immutable prepared context keyed by the complete fixed scientific/numerical spec, with exact existing boundary/sample arrays, characteristic time, scaling/inverse, energy scale, max step and bound RHS. Supply only the varying initial coordinates per cell, keeping validation at the public boundary. Reuse the actual submitted tasks for compaction's exact coverage check. Retain array immutability and avoid an unbounded cache keyed by every initial state.

**Assessment:** small–moderate; high confidence in redundant work, medium in total gain; low–medium implementation risk. Reusing existing computed arrays is numerically safer than changing arithmetic. Replacing diagonal matrix operations with scalar scaling/division is a separate measured subexperiment: it can change last-bit rounding and subsequent chaotic evolution. Compare scalar, cycle records, end states, statuses, routes and diagnostics, with exact equality for simple hoisting. Benchmark warmed cells with the same integrator/nfev, then the real tile path. Do not remove validation globally or spend disproportionate effort on dataclass slots alone.

### L3 — Separate scalar accumulation from full diagnostic histories

**Locations:** `src/lyapunov/reference.py::_run_renormalized_tangent_with_rhs/RenormalizedTangentResult`; `src/lyapunov/evaluation.py::evaluate_renormalized_tangent_runner`; `src/lyapunov/compiled_dop853.py::_integrate_compiled_dop853_segment_unchecked`; `src/lyapunov/hybrid.py::_EndpointSnapVerifier`.

**Current work and expense:** the field builds four Python history lists and converts them into arrays, then discards all cycle history and final state after extracting one scalar. Each fast segment also stores times and a copy of every accepted augmented state, converts and scans the arrays, and evaluates vectorised energy diagnostics. Requested interior grid points are constructed even though the fast driver ignores them. These costs grow with T/reset interval and accepted steps, and are plausible contributors to allocation pressure.

**Proposal:** retain the full reference/result API for teaching and equivalence tests, but allow the field path to accumulate only cumulative log, current state/tangent, nfev, energy maximum and norm-error maximum. First remove unused history storage while preserving the same arithmetic order. Then compare a preallocated/growing accepted-step buffer or a native observer that reduces the same diagnostics online. A scalar Python energy calculation in every callback may be slower than today's vectorised calculation; benchmark it rather than assume a streaming win. Do not reuse the solver's mutable output array without copying required values.

**Assessment:** moderate, particularly long T; medium confidence and implementation risk. Scientific risk is low for omitting unused histories, medium for reordered arithmetic/diagnostics. Preserve energy checks at every currently observed point, finite-state checks, accepted-step cap/endpoint detection, and positive-finite tangent/reset tests. Fallback verification needs all relevant segment gap evidence, not just the final state. Validate against full histories on route-stratified cells, malformed/failing segments, and long horizons, measuring allocations, peak/current RSS, nfev and whole-cell wall. Dropping accepted-step observation entirely is not this proposal.

### L4 — Specialise the first-flip flow while retaining its event solver

**Locations:** `src/first_flip/reference.py::_cached_dynamics/initialize_reference_dynamics/first_flip_time`; `src/lyapunov/reference.py::EulerLagrangeDynamics.__init__/flow`; `src/first_flip/field_adapter.py::_diagnostics/adapt_first_flip_result`.

**Current work and expense:** cached dynamics construction still substitutes and lambdifies both the physical flow and its full symbolic Jacobian, although first flip uses only flow. Every RHS call performs `_single_state` finite checks and NumPy/lambdified expression work. The pilot's roughly 4.95 million calls dominate much more plausibly than its 1,024 result dataclasses. Observed-event adaptation also builds `_diagnostics` once to inspect a residual and again for the returned result.

**Proposal:** avoid unused Jacobian preparation in a flow-only context, then compare a dedicated compiled four-state physical RHS under the unchanged `solve_ivp` event algorithm. Do not pad to eight states and compute a useless tangent. Keep the existing cached symbolic reference as oracle, and avoid repeating diagnostic construction in the adapter as a small adjunct. Cache already exists: adding another per-cell symbolic cache is not the missing step.

**Assessment:** potentially large for first-flip throughput, small for the duplicate adapter object; medium–high confidence, medium implementation risk. RHS arithmetic differences can perturb event time/identity, so retain lifted angles, all four directed terminal surfaces, cap equality, event residual/energy/angular-increment gates, and error/censor separation. Benchmark cached symbolic flow versus compiled flow on the same observed, censored, near-cap and low-crossing-speed cells. Validate event states, winning arm/direction, first-event ordering, and the existing `5e-8 s` convergence gate; include the pilot's slow-crossing extremum and stricter solves. A compiled event driver is a later numerical/architectural project, not a drop-in reuse of the Lyapunov segmented solver.

### L5 — Eliminate duplicate read/validation work, preserving integrity

**Locations:** `src/generation/validation.py::validate_authoritative_field`; `src/generation/hdf5.py::discover_resume_state/assert_dataset_compatible/validate_dataset/read_authoritative_field/_static_issues`; `src/generation/work_units.py::validate_tile_plan`; both field adapters' spot validators; `runners/render_finite_time_field.py::render_persisted_field`.

**Current work and expense:** final `validate_authoritative_field` invokes compatibility checking, dataset validation and authoritative reading, each of which discovers resume state and checks complete-tile checksums. `run_scalar_field` then discovers resume state again: four post-generation full discovery passes. Lyapunov's oracle reader adds another pass. Rendering does validation followed by reading, hence two. Resume compatibility plus the subsequent discovery also duplicates completed-tile scans. Each static check reads identities one tile at a time and allocates a full uint16 coverage array; the runner's planner validation allocates uint32 coverage. `read_authoritative_field` loads NumPy arrays then explicitly copies them again.

**Proposal:** one verified read session/snapshot may supply storage validation, resume state, status/range summaries and selected oracle cells, with validity scoped to an immutable file/session. Bulk-read tile metadata and avoid redundant copies of already-owned arrays. Validate rectangular coverage with a bounded row/sweep algorithm where general arbitrary plans still receive a real coverage proof. Stream values/masks for summaries; nine oracle points need not independently allocate another complete field.

**Assessment:** small current generation gain, potentially moderate resume/render and larger-N memory gain; high confidence in duplication, medium in timing; medium implementation risk. Reusing validation across file mutation creates a correctness hole: use an explicit file/session lifetime or generation identity, not a process-global “already checked” flag. Preserve rejection of corrupted complete tiles, masking of writing/not-started tiles, exact axes/provenance and conflict checks. Benchmark read-only passes separately on existing 1024²/2048² artifacts, with cold versus warm filesystem cache reported; use copied synthetic corrupt/interrupted fixtures for future validation. This audit did not create those fixtures.

## 2. Numerical/solver changes that can alter scientific results

### N1 — Address endpoint fallback without weakening its acceptance rule

**Locations:** `src/lyapunov/hybrid.py::evaluate_renormalized_tangent_hybrid/_verify_endpoint_max_step_incompatibility`; `src/lyapunov/compiled_dop853.py::_integrate_compiled_dop853_segment`; `docs/science/finite_time_stretching.md`.

**Current work and expense:** a cap excess aborts the fast attempt at its first violating segment. Eligible errors trigger a **complete** unchecked compiled replay, observing every segment to verify all excesses are endpoint-only and within the 1.01 bound. A verified cell then restarts from t=0 using compiled-RHS `solve_ivp`. The record returns fallback nfev only. Longer horizons offer more opportunities to enter this route and more discarded work when they do.

**Proposal:** first profile all three phases at T=10/20 on fixed cells. Candidate directions are an endpoint treatment that actually respects the external cap, a compiled implementation of the accepted `solve_ivp` fallback, or structured step evidence that avoids redundant reconstruction. Treat each as a separate alternative. Reusing initial-attempt evidence or continuing verification after its first violation could save part of replay, but replaces the current independent replay requirement and needs explicit review. A per-segment fallback is not equivalent to restarting the whole trajectory on `solve_ivp`.

**Assessment:** moderate potential at T=5, potentially large at longer T; medium confidence, high implementation/scientific risk. The existing science document explicitly records that `nextafter(max_step/1.01, 0)` removed overshoots but **failed the `1e-8 s^-1` rate gate at (179°,179°)**. Do not propose that already-rejected translation as an easy fix, ignore max-step violations, or fall back on arbitrary errors. The regex is only a prefilter.

Validate all audited fallback cells and their fast neighbours, lookalike/unrelated errors, all segment gaps, the five oracle cases, late first violations, and declared long horizons. Compare route semantics as well as values and diagnostics. Changes deliberately replacing route semantics need new provenance and acceptance criteria; they cannot claim bitwise compatibility with the old hybrid merely because both integrate the same ODE. Measure savings with observed route frequencies rather than extrapolating the eight fallback probes to the entire field.

### N2 — Measure whether the step cap, resets or tolerances set the work floor

**Locations:** `src/lyapunov/reference.py::SolverSpec/_resolved_interval_max_step/_solve_segment/_run_renormalized_tangent_with_rhs`; `src/lyapunov/compiled_dop853.py`; `src/first_flip/reference.py::default_solver_spec/first_flip_time`.

**Current work and expense:** the approximately 0.01 s cap and repeated solver restarts plausibly impose much of the roughly constant 1,300-plus retained RHS calls per simulated second. There is no retained histogram of cap-limited steps, rejected steps, error norms or initial-step selection cost. Solver work stability supports a hypothesis, not proof that all trajectories are cap-limited. Every Lyapunov reset starts a new solver, discarding adaptive-controller state.

**Proposal:** measure accepted/rejected steps and the fraction at the cap before experimenting with a larger cap, changed tolerances, explicit/reused first-step guesses, fewer resets, or another integrator. Study one variable at a time. Reusing allocation while fully resetting numerical state is distinct from carrying adaptive history forward. Changes to `sampling_interval` affect reference/fallback diagnostic observation; they do not directly change fast-route output sampling. Changing reset interval may also change the resolved cap via `interval/25`.

**Assessment:** potentially large if the current cap is substantially conservative; low–medium confidence, medium–high implementation risk and high scientific risk. Lower energy drift alone does not prove accurate tangent stretching or event ordering. Use strict-oracle and step/tolerance convergence comparisons across equilibria, fast rotations, chaotic regions, negative/near-zero rates and cap-boundary first flips. Retain fixed horizon, metric and initial direction; establish long-T comparison gates before accepting changed trajectories. Do not average over disagreements or enlarge tolerances after seeing results. Fixed-step, symplectic, normalized-tangent ODE or alternative state formulations belong to separately validated numerical studies, not low-risk optimisation.

## 3. Architectural changes

### A1 — Diagnose worker retention before extending reuse

**Locations:** `src/generation/runner.py::run_scalar_field/_open_pool/_close_pool`; `src/lyapunov/compiled_dop853.py::_integrate_compiled_dop853_segment_unchecked`; `investigations/performance/probe_worker_lifetime.py`, `probe_worker_lifetime_ab.py`, `probe_runner_recycling_candidate.py`.

**Current work and expense:** deterministic pool recycling limits observed RSS growth but repeatedly pays setup/shutdown. The budget counts pool-wide returned cells, not per-worker cells, steps, allocations or CPU time. Warm-ups, verification replays and failed partial work are not counted separately. T=20 cells allocate/integrate far more than T=1 cells. Per-worker scheduling imbalance further weakens cell-count-to-memory assumptions.

**Concrete retention hypothesis:** inspection of the installed SciPy `_ode.py::dopri5/dop853.reset` shows `self.call_args` retaining bound `self._solout`, a Python reference cycle. The integrator also holds the prototype's `observe` closure and accepted-state lists. This is a specific place to inspect object lifetime, **not a demonstrated cause of the observed RSS slope**. Python cyclic collection, native allocation retention and allocator residency may behave differently. The historical probes call `gc.collect()` in the coordinator after receiving results; that does not collect child-process objects.

**Proposal:** perform a bounded worker-local allocation/lifetime experiment, counting surviving integrator/callback objects and Python allocations, observing native/current RSS before/after worker-local collection and release. Contrast segment-heavy fast cells, fallback cells and first-flip cells at T=1/5/20. If there is removable retention, release ownership or reuse correctly reset workspaces before considering longer lifetimes. Otherwise investigate a resource budget informed by actual per-worker work/RSS, retaining a hard bound. A warmed spare pool or staggered replacement could overlap lifecycle with computation, but increases simultaneous memory and shutdown complexity.

**Assessment:** large potential if safe reuse becomes possible; medium confidence in the opportunity, low in a particular cause; medium implementation risk, low direct numerical risk for pure ownership changes. Workspace reuse or solver continuation raises numerical risk. Preserve identical calculations, bounded errors and worker cleanup. Run mixed-route create/interruption/resume checks and current-RSS measurements under a declared memory ceiling. Never treat 4,096/unlimited lifetimes as justified by the earlier 2,048 promotion, or transfer the Lyapunov retention diagnosis automatically to the first-flip consumer.

### A2 — Generate several observation horizons from shared prefixes

**Locations:** README batch loop; `runners/generate_lyapunov_periodic_field.py`; `src/lyapunov/reference.py::_run_renormalized_tangent_with_rhs`; `src/lyapunov/hybrid.py`; `src/generation/hdf5.py::CompletedTile/FieldDefinition`; first-flip reference/adapter for cap products.

**Current work and expense:** the documented T=1,2,5,10,20 sweep starts five independent runs, each integrating from zero and recreating pools. That nominally integrates 38 s of trajectory per cell to obtain a maximum horizon of 20 s. Current HDF5 retains scalars and aggregate tile diagnostics, not the final state/tangent/log accumulator necessary for a trustworthy dynamics restart. Existing completed T=5 files cannot be extended to T=20 from the scalar alone.

**Proposal:** a multi-horizon cell evaluator could emit prefix scalars and prefix diagnostic maxima at declared reset boundaries, then persist separate horizon products or a versioned horizon dimension. A crash checkpoint additionally needs exact reference/tangent state, cumulative signed log, initial energy, absolute time, route state and compatible numerical provenance. The ideal no-extra-work prefix reuse removes 18/38 = 47.4% of nominal integrated horizon versus five independent runs (1.9x compute throughput); this is an upper-level opportunity, not a wall prediction.

**Assessment:** large for repeated-horizon workflows, no benefit to an isolated already-generated single horizon; medium confidence in equivalence, high implementation risk. Later fast-path failure currently makes an entire long-horizon result use `solve_ivp`, whereas an earlier shorter horizon may legitimately remain fast. Prefix outputs must preserve each horizon's own routing, diagnostics and validity, or clearly adopt a newly validated contract. Preserve exact boundary construction; do not assume independently generated floating grids always share bit-identical prefixes.

For first flip, a valid longer-cap scalar already supports shorter **threshold products** via the documented strict inequality, with no new integration. New shorter-horizon artifacts require attention to prefix validity and provenance; full-horizon diagnostics cannot reproduce every earlier validity decision. Extending censored cells requires saved continuous lifted state and original event reference angles. Validate every emitted horizon against independent runs, including late fallback, prefix-valid/later-invalid cells, exact-cap events and partial restart. Benchmark complete sweep wall including persistence and lifecycle, not just the longest solve.

### A3 — Decouple task batching from persistence tiles

**Locations:** `src/generation/runner.py::run_scalar_field/_evaluate_bound_cell/_compact_tile`; `src/generation/work_units.py::ScalarCellTask/tasks_for_work_unit`; both adapters' tile summarisers.

**Current work and expense:** every cell serializes a task and returns `CellOutcome`, the original task, `ScalarEvaluation` and a diagnostics dataclass. A tile requires 64 individual futures/messages; 1024² means over one million task/result exchanges. Returned results are compact: full trajectories/cycle histories are **not** sent through IPC. Each cell also calls `os.getpid`, `resource.getrusage` and `platform.system` for RSS reporting. A tile barrier creates a short tail and prevents overlap with coordinator writes.

**Proposal:** compare small chunks (for example 2/4/8 cells) under the same science and persistence tiles, then, if needed, a bounded queue spanning a few tiles. Retain global indices, assemble exact tile coverage, and commit only complete verified tiles. Return packed primitive arrays or worker-batch summaries only if serialization is measured material. A whole tile per worker can create larger stragglers; increasing storage tile size is not required to reduce IPC. Sample resource diagnostics at a declared batch boundary rather than blindly deleting them. If future width changes are tested, verify actual numerical-library thread counts: current environment settings use `setdefault`, and eager imports can load NumPy before that code runs.

**Assessment:** small at current T=5, potentially moderate at short T or after compiled acceleration; medium confidence/risk, low scientific risk if cells remain independent. The 93.3% occupancy proxy suggests only about 6.7% visible four-worker capacity gap in that evaluation phase, not an enormous dispatch win. T=1's proxy is lower, about 88.9%. Test mixed routes and variable-duration first-flip cells, not only a cheap synthetic evaluator. Measure coordinator CPU, IPC bytes, tail wait and end-to-end throughput. Test out-of-order results, duplicate/missing cells, bounded outstanding work, interruptions, exact status/route placement, policy accounting and worker termination. A wider pool needs explicit memory/host evidence; `os.cpu_count()` alone is not a throughput prescription.

### A4 — Improve HDF5 access/storage layout only when it becomes material

**Locations:** `src/generation/hdf5.py::create_dataset/write_completed_tile/_checksum_from_file/_checksum_parts`; `src/generation/runner.py::run_scalar_field`.

**Current work and expense:** each 8×8 tile opens/closes HDF5, validates arrays, serializes three JSON records, computes a candidate SHA-256, writes a WRITING marker and flushes, writes payload and flushes, rereads stored payload to verify its checksum, stores the checksum and flushes, then marks COMPLETE and flushes. Each field dataset uses 8×8 chunks with gzip level 4, shuffle and Fletcher32. There are 16,384 transactions at 1024² and 65,536 at 2048². Tiny values chunks hold 512 raw bytes, status/route chunks 64 bytes each.

**Proposal:** after L5, consider a coordinator-owned open writer session with cached dataset handles while preserving transaction ordering/readback. Separately benchmark larger storage chunks or less repetitive metadata encoding; larger chunks that contain many existing tiles can cause repeated partial-chunk recompression. Compression changes must retain integrity and explicit format/provenance. Overlap coordinator commits with bounded future computation only through A3's resource accounting. Do not add multiple worker writers to the same file as a casual optimisation.

**Assessment:** small current generation benefit, potentially moderate throughput/storage benefit after kernel acceleration or at much larger N; high confidence in repeated operations, medium in payoff; medium–high implementation risk. Scientific arithmetic is unchanged, but persistence/recovery correctness risk is high. Validate interrupted writes at every transaction phase, identical/conflicting duplicate writes, damaged payloads and metadata, masked incomplete regions and compatible/incompatible resumes. Checksums include timing/PIDs-related diagnostics/provenance: whole-file hashes will differ across scientifically identical timed runs. Compare scientific payloads separately. Do not remove readback, checksums or completion-order guarantees to chase the present 1% write bucket.

### A5 — Reuse verified cells during nested resolution escalation

**Locations:** `src/state_space_fields.py::full_periodic_angle_axis`; `src/generation/work_units.py::tasks_for_work_unit`; `src/generation/hdf5.py::FieldDefinition/assert_dataset_compatible`; `src/lyapunov/field_adapter.py::periodic_lyapunov_field_definition`.

**Current work and expense:** every new N creates a separate grid and integrates all cells. For a doubling, the mathematical coarse coordinates occupy every other index in each fine axis; 25% of the finer grid is shared. Current resume rightly requires the exact definition/axes/tile plan and cannot import a different resolution. There is no cross-artifact cell cache.

**Proposal:** a future lineage-aware import operation could copy only verified cells with exactly matching stored coordinates and complete physical/numerical/evaluator provenance, computing the other 75%. A coarse tile is not a fine tile, so reconstruct cell placement and new transaction identities rather than transplant checksums. Confirm floating coordinates bitwise, not by assuming formula equivalence or rounding nearby coordinates into a cache key. Reusing across the inspected historical Git revisions requires explicit scientific compatibility review; today's whole-definition resume should continue to reject those mismatches.

**Assessment:** moderate for repeated doubling (up to 25% fewer new cell evaluations when an accepted coarse field already exists); high confidence in overlap, medium in transfer safety; medium–high implementation risk. Validate reused cells against independently computed fine-grid cells, preserve invalid/error semantics and lineage, and test corrupt-source rejection. Do not silently relax `assert_dataset_compatible`. Benchmark import validation plus generation, including any loss of task batching efficiency. Caching arbitrary nearby chaotic states is not justified.

## 4. Speculative approaches with high upside

### S1 — Compile across the solver and observer boundary

**Locations:** `src/lyapunov/compiled.py::compiled_reference_and_tangent_rhs/compiled_rhs`; `src/lyapunov/compiled_dop853.py::_integrate_compiled_dop853_segment_unchecked`; `src/lyapunov/reference.py::_run_renormalized_tangent_with_rhs`; `src/lyapunov/hybrid.py`.

**Current work and expense:** compiling the eight-variable arithmetic does not remove Python callbacks, return-array allocation, accepted-step copying or Python renormalisation/energy bookkeeping. Billions of recorded RHS calls make the boundary itself a plausible remaining ceiling. The kernel already fuses flow and exact JVP; constructing a dense Jacobian would move backwards. Trigonometric evaluation and allocation inside the kernel may also matter, but no retained profile isolates them.

**Proposal:** prototype a single-cell native/Numba solver loop, or a supported native callback interface, with reusable stage/output buffers and compiled diagnostic reductions. Start with one serial cell before batching. Preserve the DOP853 tableau, error norm/controller, accepted-step cap, endpoint decisions, reset times and floating operation order as far as required. A kernel cannot simply be passed as a C function to today's Python callback API without changing the integration boundary. Compile a fallback-equivalent path separately if fallback still dominates. Only after attribution consider trig common-subexpression changes or in-place JVP; reusing an RHS output array through SciPy can alias retained solver stages unless ownership is verified.

**Assessment:** potentially transformative warm-compute improvement; medium confidence in opportunity, low in factor; high engineering and numerical risk. Solver rewrites or different library DOP853 implementations are not numerically interchangeable by name. Benchmark native time, callback counts, allocations, accepted/rejected steps and total nfev on the identical cell stream. Require the established RHS/JVP tests, full cycle/final-state comparisons, deliberate failures and fallback decisions, and independently specified long-horizon convergence gates. Disable reassociation/fast-math experiments initially. Keep the mathematical and integration-boundary oracles independent. Include cold compilation and current pool costs in final throughput claims: even infinite evaluator speed cannot erase lifecycle and coordinator costs.

### S2 — Independent compiled batches, accelerators, symmetry and sampling changes

These are alternatives to investigate after the single-cell ceiling is measured, not one combined implementation proposal.

| Approach and exact seam | Current expense and proposed organisation | Impact / confidence / implementation risk | Scientific risks and required benchmark/validation |
| --- | --- | --- | --- |
| CPU batches / GPU: `compiled.py`, `compiled_dop853.py`, `runner.py` evaluator binding | Independent cells repeat a tiny eight-state solve. Keep state/stages in structure-of-arrays batches with per-cell adaptive state and active masks; return only scalar/diagnostics. | Potentially transformative; low confidence in net factor; high risk | Divergent adaptive steps, fallback and first-flip stop times waste SIMD/GPU lanes. A flattened aggregate ODE shares an error norm and can couple acceptance across cells; `vectorized=True` or `np.vectorize` is not an independent-cell solver. Validate each cell's cap/error norm, statuses and horizon against oracles. Measure transfer/JIT cost, lane utilisation and full batch wall; require useful float64 throughput. Benchmark small CPU batches first. |
| Reflection: `state_space_fields.py::full_periodic_angle_axis`, both field adapters, `compiled.py` | The zero-velocity physical flow has simultaneous sign-reflection symmetry; the first-flip pilot records close reflected scalar agreement. Investigate evaluating one representative of each reflection pair. | Large, approaching a twofold compute reduction only if accepted; medium confidence in mathematical opportunity, low in exact execution equivalence; high risk | For Lyapunov, reflect the tangent correctly: the reflected initial tangent differs by sign, and only the norm-based observable removes that sign mathematically. Branch endpoints, roundoff, fallback routes and diagnostics may differ. First-flip winning direction must reverse. Verify torus indexing/fixed points, scalar symmetry and route/validity semantics across long T. Mirroring scalars cannot fabricate independent diagnostics or provenance. No arm-exchange symmetry is assumed. |
| Adaptive spatial refinement: grid planning, field definition, HDF5 schema and renderer | Uniform N² sampling spends equal effort in smooth and intricate regions. A separate sparse/refined product could spend cells according to a declared error criterion. | Potentially transformative for a different product; low confidence; high risk | This changes sampling, coverage and interpretation; it is not acceleration of the identical N² field. Narrow structures and chaotic boundaries can be missed. Validate against held-out uniform samples and convergence criteria, retain coordinates/refinement provenance and an appropriate renderer. Visual similarity is insufficient. |

## Scaling model and validation requirements

For fixed policy, a useful accounting model is:

```text
cells C = N²
tiles M = ceil(N/8)²
full-tile pool count approximately ceil(C / 2048)
cycles K = T / 0.25

wall ~= pool_count * lifecycle
        + C * mean_cell_cost(T, route mix) / effective_worker_parallelism
        + M * commit_cost
        + planning/validation/rendering
```

The first term is not a one-time startup cost. It scales with N² at a fixed lifetime limit. The second has at least roughly linear T work, plus route-dependent replay/fallback and allocation costs. Neither mean cell cost nor safe memory budget is constant across horizons or consumers. First-flip integration instead depends on `min(event time, horizon)`; increasing the cap concentrates extra work in the censored population.

The working scalar payload is 10 MiB at 1024², 40 MiB at 2048² and 160 MiB at 4096², before masks, redundant copies, uint32/uint16 coverage arrays, tile-plan objects, HDF5 caches and plotting buffers. At 12,000² that payload alone is about 1.34 GiB. Current per-worker allocation/retention and coordinator whole-field passes are independent limits. A tiled writer does not by itself make the whole workflow memory-bounded with respect to N.

For any future experiment:

- Fix the revision/environment, actual process policy, complete spec, coordinates, route strata, test ordering and memory ceiling before timing. Use the 16-cell route sample plus a mechanically fixed mixed-route set, and add targeted long-T/first-flip edge cases. The five reference cases and nine field spots are regression gates, not representative performance or scientific coverage of all cells.
- Record cold and warmed timings separately. Measure imports/JIT, all fast/replay/fallback phases, accepted/rejected steps, actual total RHS calls, segment count, diagnostic/normalisation time, allocations, worker current and peak RSS, coordinator work, persistence and final validation. First-flip's `wall_seconds` covers `solve_ivp` only; its adapted `elapsed_seconds` excludes postprocessing. Lyapunov's elapsed value covers the full hybrid but excludes per-cell specification construction. Do not compare those timer labels as though they have identical scope.
- Use paired, interleaved same-host repetitions. Profile short samples for attribution, then disable intrusive instrumentation for timing; thousands of per-RHS Python timing calls would distort the workload. Reconcile phase sums with outer wall and report uncertainty/route mix. Measure real-run gains after microbenchmarks, not only an isolated faster helper.
- For implementation-only changes, seek exact values/statuses/routes/issues and scientific diagnostic equality. Exclude elapsed time/PIDs/RSS from equality expectations; retain checksummed payload integrity separately. For arithmetic/solver changes, use the predeclared gates from `compiled_equivalence.py`: rate `1e-8 s^-1`, cycle logs `5e-8`, final Candidate-A reference/tangent distances `1e-7`, energy diagnostic difference `1e-8`, plus status/validity agreement. These are bounded T=5 gates, not automatic evidence for arbitrary T.
- Compare tangent direction and cycle histories, not just energy or final scalar. For longer chaotic trajectories, independent strict-solver convergence and scientifically agreed acceptance criteria are needed; a failure of pointwise agreement is not permission to discard the criterion silently. First flip additionally needs first-event identity/time, residual, crossing speed, competing margin, accepted angular increments and strict censor-cap semantics.
- Use `tests/lyapunov/test_reference.py`, `test_compiled.py`, `test_compiled_dop853.py`, `test_hybrid.py`, `test_field_adapter.py`; `tests/first_flip/`; `tests/generation/`; and `tests/test_operational_runners.py` as the existing gate map. Future acceleration work needs representative horizon and memory tests beyond these primarily bounded fixtures. Assert deterministic orientation, duplicate/missing-cell rejection, interrupted writing, corrupted-complete failure, same-/cross-policy resume semantics and exact worker cleanup.

## What not to optimise yet

- **Do not repeat the 1,024 -> 2,048 promotion.** It is already the default. Do not increase it again just because startup is costly; T-dependent residency is now visible in local evidence.
- **Do not prioritise generic symbolic caching for the current Lyapunov fast/fallback path.** Neither constructs `EulerLagrangeDynamics` per field cell. Repeated symbolic construction is real in the reference grid/sweep and cached per worker for first flip. Optimise the path actually used.
- **Do not pursue QR, trajectory plotting, animation or bob-position computation for field generation.** They are absent from the scalar hot path. Keep reference/teaching APIs readable rather than rebuilding them to resemble the operational runner.
- **Do not tune JSON formatting, progress printing, the fallback regex or individual dataclasses first.** Progress is already decile-throttled, manifests are written once, and the recorded route-wrapper remainder is only about 0.016–0.018 ms in its bounded probe. Dataclass/input preparation should be measured within L2, not assumed dominant.
- **Do not remove checksums, flush ordering or scientific validity checks.** The named write bucket is about 1%; the risk/return is poor. Consolidating redundant checks is different from weakening them.
- **Do not swap multiprocessing for threads or fork without evidence.** The present code has Python callbacks, process-local globals, and legacy solver boundaries; thread safety/GIL behaviour would need validation. Spawn isolation and bounded termination are part of the earned execution behaviour.
- **Do not increase solver step size, suppress cap errors, reduce float precision, enable fast-math, or stop a fixed-T Lyapunov cell when its value “looks settled” as implementation cleanups.** These change numerical or scientific meaning. The cap-translation rejection is concrete prior negative evidence.
- **Do not optimise rendering to explain multi-hour dynamics.** Rendering is separate. Its two HDF5 validation passes, masked-array copies, full-size first-flip overlay, TeX and 600-dpi raster allocation are relevant if rendering itself is slow, but no render phase timing was found. The nominal 7.2×6.0 inch PNG is about 4,320×3,600 pixels (roughly 59 MiB for one RGBA buffer); PNG/PDF draws and masks can add more. Profile that command independently before changing quality or export defaults; preserve invalid/censored colours, orientation, scale and labels.
- **Do not use another full 1024²/2048² run to find the first bottleneck.** Existing evidence already locates the major buckets. Small route-stratified and lifecycle experiments can discriminate the remaining hypotheses much more cheaply.
- **Do not treat the historical probes as ready-to-run current benchmarks.** Their default paths/policies and evidence-writing behaviour need explicit review. No proposal in this report authorises running them.

## Inspection record and repository state

The directory inventory before creating this report contained 51 Python files, 6 Markdown files, 9 JSON records, 9 HDF5 files, 9 PNGs, 9 PDFs, 60 existing bytecode files, three `.gitignore` files and one `.DS_Store`. All Python files were parsed read-only for inventory; execution paths, tests and investigation measurement boundaries were inspected as described above. Existing binary images/PDFs were inventoried and hashed, not visually reviewed: their pixels do not establish generation performance. Bytecode and `.DS_Store` were inventoried/hashed, not treated as source.

Inspected source/documentation areas:

- Root `__init__.py`, `README.md`; `docs/architecture.md`, both `docs/science/*.md` files, and `docs/pedagogy/sensitivity_to_lyapunov.md`.
- `src/state_space_fields.py`, `src/__init__.py`; all five `src/generation/*.py` files; all ten `src/lyapunov/*.py` files; all three `src/first_flip/*.py` files.
- All four `runners/*.py` files, including package initialisation, both generation CLIs and the renderer.
- `tests/test_state_space_fields.py`, `tests/test_operational_runners.py`, all generation, Lyapunov and first-flip test files and their fixtures/package initialisers.
- `investigations/performance/README.md`; all six Python investigation utilities (`analyze_persisted_timings.py`, `probe_pool_lifecycle.py`, `probe_route_stratified_cells.py`, `probe_worker_lifetime.py`, `probe_worker_lifetime_ab.py`, `probe_runner_recycling_candidate.py`) and all five retained JSON evidence/design records.
- `outputs/lyapunov/reference_vs_compiled_equivalence.json`; first-flip pilot HDF5/JSON; every HDF5/JSON in `outputs/finite_time_field/001_512_squared`, `002_1024_squared`, `003_2048_squared` and `004_Tsweep/data`; output ignore rules and derivative inventories.
- Repository context outside this directory: `AGENTS.md`, `README.md`, `ROADMAP.md`, `documentation/README.md`, relevant dependency declarations in `pyproject.toml`, production `src/double_pendulum/models/lagrangian.py` imports/equation-cache entry, and installed `.venv/lib/python3.12/site-packages/scipy/integrate/_ode.py` for the actual solver allocation/callback ownership boundary. No dependency installation/update was performed.

Read-only commands comprised Git status/revision inspection, `rg`, `find`, `cat`, `sed`, `wc`, and inline Python with `-B`/`PYTHONDONTWRITEBYTECODE=1` for JSON/HDF5 reads, source parsing, derived statistics and SHA-256 fingerprints. No benchmark, pytest, Dash server, renderer or field runner was started. Hashes of the pre-existing prototype tree were recorded before report creation and checked afterwards; inspection does not rely on Git tracking of ignored artifacts alone.

Initial `git status --short` was empty. Final expected sole change, verified after writing this report:

```text
?? development/chaos_content/prototypes/state_space_maps/ASTRA_SPEEDUP.md
```

## Recommended optimisation sequence

The smallest useful programme is six bounded decision steps; each is a proposal for later work, not an action taken by this audit.

1. **Correct the duration handoff and establish trustworthy small-run completion.** Implement L0 separately, check T=1/5/10 on tiny fields and reject mismatched artifact/spec validation early. Keep the existing non-default artifacts intact until their actual horizon-specific checks are run. This is low effort and prevents collecting misleading completion evidence.
2. **Measure cold-worker cost and retention in one controlled experiment.** Use fixed fast/fallback cells at T=1/5/20, the current 2,048-cell limit, worker-local allocation/GC observations and an explicit RSS ceiling. Separate imports, JIT, warm solve and teardown. Trial only the best-supported L1 ownership/cache/import change first. This determines whether lifecycle can fall materially without paying for larger worker memory.
3. **Profile a warmed cell and make one small allocation/preparation A/B.** Split native integration, callbacks, accepted-step recording, renormalisation/energy and preparation; count discarded route work as well as returned nfev. Test L2 hoisting and the simplest L3 history omission under unchanged solver decisions. If their contribution is small, stop polishing Python objects and move directly to the next decision.
4. **Choose one route across the compute ceiling.** If callbacks/segment overhead dominates, build a single-cell compiled-loop prototype (S1) against existing oracle gates. If the long-T fallback premium dominates, investigate one N1 alternative while preserving the rejected-cap-translation evidence. For a first-flip workload, the cheaper corresponding experiment is L4's compiled four-state RHS under the unchanged event solver. Do not start a GPU or broad scheduler rewrite yet.
5. **For horizon sweeps, test prefix reuse on the same small cell set.** Emit T=1/2/5/10/20 products and compare each against independent runs, especially late-fallback and prefix-valid cases. This directly tests A2's avoided-work benefit without requiring a new high-resolution field. If the workflow is resolution escalation instead, substitute A5's exact shared-cell import experiment.
6. **Re-measure the real runner after the winning compute change.** Use a fixed mixed-route 64² field, paired repetitions, create/interruption/resume and worker-stop checks. Test small chunks or bounded cross-tile dispatch only if IPC/tail/coordinator work is now material; consolidate repeated HDF5 validation before changing transaction semantics. Advance resolution only after measured end-to-end throughput and memory justify it. This final step identifies the new ceiling rather than assuming microbenchmark gains survive the pipeline.
