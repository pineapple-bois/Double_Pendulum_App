# First-flip compiled RHS promotion

## Outcome

The compiled four-state RHS is activated as the guarded operational default for
the validated standard first-flip field. All scientific and operational gates
passed. Three alternating-order 64² T=5 A/B pairs produced a median **2.170×
end-to-end speedup**, above the required 1.5× gate.

## Architecture and eligibility

`src/first_flip/compiled.py` is the production copy of the validated Numba
four-state Euler–Lagrange kernel. It changes only the callable supplied as
`solve_ivp(fun=...)`; `first_flip_time` still owns continuous lifted absolute
angles, four signed terminal surfaces, positive crossing direction, DOP853,
`rtol=1e-9`, `atol=1e-11`, `max_step=sqrt(1/9.81)/32`, root refinement,
attribution, censoring, energy diagnostics, angular-increment diagnostics, and
all result/status semantics. The independent Python RHS remains the stricter-
spot oracle and trusted route.

Compiled dispatch is allowed only for the exact unit/equal-link parameters,
zero initial velocities, T=5, default solver, and existing residual/energy/
increment gates on the validated Darwin ARM64, macOS 15.7.9, Python 3.12.3,
NumPy 2.5.2, SciPy 1.18.0, Numba 0.67.0, llvmlite 0.49.0, LLVM 22.1.0 build.
JIT-disabled, unsupported, or ineligible cases use the unchanged trusted path.

Each spawned worker warms and retains its own compiled callable. Numba's normal
compatible disk cache supplies later worker/pool cache hits. Initialization
unavailability is recorded and routes cells through the trusted RHS. A compiled
numerical rejection triggers one explicit trusted replay; the trusted result
retains its real invalid/error/censored/observed semantics. Arbitrary programming
exceptions propagate and are not converted to recovery or censoring.

## Provenance and persistence

The persisted routes are distinct:

- `numba_rhs_solve_ivp_first_flip_v1` for accepted compiled results;
- `solve_ivp_first_flip_reference` for trusted results.

Compiled definition provenance includes the implementation identity, full
kernel-module SHA-256, nopython/cache/fastmath flags, Python ABI, platform,
NumPy/SciPy/Numba/llvmlite/LLVM versions, and trusted recovery identity. The
compiled route vocabulary contains both possible routes. Trusted/ineligible
definitions retain the legacy trusted definition and single route.

The existing canonical HDF5 definition check therefore rejects compiled/trusted
cross-resume before writing. Same-definition interrupted/resume behavior remains
valid. Existing artifacts are not mutated or made artificially compatible.

## Scientific validation

The saved 37 feasibility coordinates were replayed through the production
compiled and independent Python paths. All expected-valid cases explicitly
produced completed-valid adapter results. Classification, attribution, link/sign,
raw event counts, adapter outcomes, and RHS counts matched exactly. The established
gates remained unchanged: event time 5e-8 s, event state 5e-7, triggering residual
and difference 1e-10, normalized energy drift and difference 5e-9, and accepted
angular increment strictly below 0.5.

Focused tests additionally cover supported and unsupported dispatch, ineligible
specifications, cold/cache-hit initialization, forced initialization failure,
trusted recovery after numerical rejection, programming-error propagation,
spawn execution, persisted route/provenance, same-definition resume, and both
directions of compiled/trusted definition mismatch.

## Bounded operational A/B

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_compiled_promotion
```

The benchmark used one fresh cache scope, so pair 1 includes cold compiled
initialization and later pools/runs exercise cache hits. Every field used the
unchanged 64² periodic grid, 8×8 tiles, four spawn workers, chunksize one, and
2,048 returned cells per pool (two pools/run).

| Pair/order | Compiled wall | Trusted wall | Speedup | Compiled setup | Trusted setup | Compiled evaluation | Trusted evaluation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 C/T | 27.809 s | 61.787 s | 2.222× | 2.943 s | 8.132 s | 23.657 s | 52.405 s |
| 2 T/C | 29.796 s | 64.650 s | 2.170× | 2.885 s | 9.324 s | 25.694 s | 54.049 s |
| 3 C/T | 29.553 s | 62.827 s | 2.126× | 2.603 s | 8.064 s | 25.731 s | 53.578 s |

Persistence was 0.159–0.177 s and shutdown 0.731–0.807 s. Peak worker RSS was
232,177,664 bytes compiled (cold maximum) and 202,375,168 bytes trusted. All
workers stopped.

Every field had 1,742 observed and 2,354 censored completed-valid cells, with
zero invalid or execution-error cells. Compiled fields persisted 4,096 compiled
routes; trusted fields persisted 4,096 trusted routes. Axes, statuses, and censor
masks were identical in all pairs. Maximum compiled/trusted observed event-time
difference was 5.576e-12 s. All authoritative checksum validation and all nine
stricter Python-oracle spots per field passed; the largest spot difference was
9.728e-11 s, far inside 5e-8 s.

Evidence: `../evidence/current/first_flip_compiled_promotion_64.json`.

## Validation

```text
204 passed in 47.43s
```

The combined suite covered all state-space-map tests, current performance tests,
S1 history tests, and Experiment 020. Import/compile, Markdown-link, and
`git diff --check` validation also passed.

## Changed paths

- `src/first_flip/compiled.py`
- `src/first_flip/field_adapter.py`
- `src/first_flip/__init__.py`
- `tests/first_flip/test_compiled.py`
- `investigations/performance/tools/first_flip_compiled_rhs.py`
- `investigations/performance/tools/benchmark_first_flip_compiled_promotion.py`
- `investigations/performance/evidence/current/first_flip_compiled_promotion_64.json`
- this report and `investigations/performance/README.md`

No solver, event, tolerance, grid, multiprocessing, scheduling, persistence, or
rendering policy was redesigned.
