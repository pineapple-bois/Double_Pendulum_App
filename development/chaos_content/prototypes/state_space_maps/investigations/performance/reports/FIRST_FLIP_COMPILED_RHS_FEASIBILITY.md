# First-flip compiled-RHS feasibility

## Decision

**GO for a separate promotion task.** A Numba-compiled four-state physical RHS
preserved the complete tested Experiment 020 event contract and produced about
2.08× warm cell-compute acceleration. Weighting observed and censored timing
samples by the existing 512² T=5 field, then retaining its measured non-evaluation
wall, gives a plausible **1.80× end-to-end field estimate**. This exceeds the
1.5× decision gate. No production route was promoted.

## Prototype architecture and preserved contract

`tools/first_flip_compiled_rhs.py` contains one investigation-only Numba kernel
for the physical state $(\theta_1,\theta_2,\omega_1,\omega_2)$. Its equations and
parameter order match the current Euler–Lagrange flow. The operational
`first_flip_time` gained only a private `_rhs_override` test hook; when omitted,
the existing `EulerLagrangeDynamics.flow` path is unchanged.

The prototype passes the compiled callable into the same `first_flip_time` code.
Consequently the following remain owned by the existing implementation without
duplication or replacement: continuous absolute lifted angles; four signed
$s(\theta_i(t)-\theta_i(0))-2\pi$ surfaces; `terminal=True`; `direction=+1`;
SciPy `solve_ivp`; DOP853; `rtol=1e-9`; `atol=1e-11`;
`max_step=sqrt(1/9.81)/32`; the 5 s horizon; SciPy root refinement; attribution;
censoring; accepted-state energy and angular-increment diagnostics; result and
field status/value adaptation. Grid, multiprocessing, persistence, and provenance
were not exercised through a new route and were not changed.

## Representative cells and validation

The benchmark reads the checksum-valid existing 512² field and selects:

- all four signed Experiment 020 cases plus its 4.795 s near-horizon case;
- 16 midpoint quantiles of the observed-time distribution, spanning 1.209–4.797 s
  and explicitly covering early, medium, and near-horizon flips; and
- 16 midpoint quantiles of the censored cells in stable flat-index order, all of
  which integrate the full 5 s horizon.

There are 37 distinct comparison cases. The 32 mechanically selected field cells
are the timing/weighting sample; the five named Experiment 020 cells strengthen
contract validation without biasing the field estimate.

All **37/37** comparisons passed. Observed/censored outcome, solver status and
validity, winning link/sign, attribution, raw event counts, field outcome/status,
and RHS evaluation counts matched exactly. Worst differences were:

| Quantity | Worst difference | Gate |
| --- | ---: | ---: |
| Event time | 1.368e-13 s | 5e-8 s |
| Event-state component | 1.707e-12 | 5e-7 |
| Event residual | 1.688e-13 | 1e-10 |
| Compiled triggering residual | 3.553e-15 | 1e-10 |
| Normalized energy diagnostic | 1.099e-14 | 5e-9 |

Both paths remained below the existing energy, residual, and accepted-angular-
increment validity gates. No attribution or cap-boundary disagreement occurred.

## Warm timings

Each case was warmed, then measured nine times with alternating trusted/compiled
order. Times include the complete first-flip result and field adaptation, not
only the kernel. One-time Numba compilation is excluded because the question is
steady worker evaluation feasibility.

| Outcome | Cells | Trusted median | Compiled median | Median speedup | Speedup range | Mean RHS evaluations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Observed | 16 | 24.307 ms | 11.676 ms | **2.079×** | 2.062–2.102× | 3,202.25 |
| Censored | 16 | 50.249 ms | 24.044 ms | **2.091×** | 2.056–2.111× | 6,035.75 |

Observed cells ranged from 1,481 to 5,789 RHS evaluations; censored cells ranged
from 6,026 to 6,098. Censored cells gain very slightly more in median terms, but
the distributions overlap: the result supports essentially the same factor for
event-terminating and full-horizon cells, with larger absolute savings for the
latter.

Separate instrumented representative calls estimate that the trusted physical
RHS consumes 58.4% of observed evaluator wall and 58.6% of censored evaluator
wall. The compiled RHS consumes about 16.2% and 16.3%, respectively. These are
inclusive wrapper timings and therefore approximate, but their 3,005/6,026 call
counts exactly match solver `nfev`.

## Weighted 512² estimate

The existing field contains 111,520 observed cells (42.5415%) and 150,624
censored cells (57.4585%). Because total field work is additive, arithmetic means
of the distribution-aware per-cell medians are used:

```text
trusted weighted cell = 0.425415 * 26.946 ms + 0.574585 * 50.376 ms
                      = 40.408 ms
compiled weighted cell = 0.425415 * 12.959 ms + 0.574585 * 24.090 ms
                       = 19.354 ms
cell-compute speedup = 2.088×
```

The prior 512² run measured 3,411.436 s evaluation and 3,994.485 s total. Holding
all setup, shutdown, persistence, validation, and other wall unchanged:

```text
estimated evaluation = 3411.436 / 2.088 = 1633.982 s
estimated total = 3994.485 - 3411.436 + 1633.982 = 2217.031 s
estimated whole-field speedup = 3994.485 / 2217.031 = 1.802×
```

This is an explicitly weighted estimate, not a measured compiled field result.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_compiled_rhs
```

Evidence: `../evidence/current/first_flip_compiled_rhs_feasibility.json`.

## Tests and validation commands

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m pytest \
  development/chaos_content/prototypes/state_space_maps/investigations/performance/tests \
  development/chaos_content/prototypes/state_space_maps/tests/first_flip \
  development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/test_first_flip_event_contract.py \
  development/chaos_content/prototypes/state_space_maps/tests/generation \
  development/chaos_content/prototypes/state_space_maps/tests/test_operational_runners.py -q
```

Result: **54 passed in 21.66 s**. Import/compile checks for the affected modules,
performance-investigation Markdown relative-link validation, and
`git diff --check` also passed.

## Limitations

- This is a warm, single-process representative-cell prototype, not an
  operational multiprocessing field benchmark. Promotion must validate worker
  initialization, route/provenance identity, persistence/resume, and bounded
  field output separately.
- Quantiles approximate observed time/cost distribution. Censored cells are
  spatially sampled because the persisted scalar cap does not retain every
  cell's individual cost.
- The estimate assumes the existing non-evaluation wall is unchanged and does
  not claim scheduling, setup, or persistence savings.
- Agreement is strong for the declared T=5 transversal sample, not proof for
  grazing, tied, other-parameter, or longer-horizon cases.
- A promotion task must decide compiled-code initialization/caching and supported
  builds without broadening the Experiment 020 contract.

## Files changed

- `src/first_flip/reference.py`: private investigation-only RHS injection hook.
- `investigations/performance/tools/first_flip_compiled_rhs.py`: compiled kernel.
- `investigations/performance/tools/benchmark_first_flip_compiled_rhs.py`:
  selection, validation, timing, attribution, and weighted estimate.
- `investigations/performance/tests/test_first_flip_compiled_rhs.py`: focused
  kernel, signed-event, near-horizon, and censoring checks.
- `investigations/performance/evidence/current/first_flip_compiled_rhs_feasibility.json`:
  complete reproducible evidence.
- this report and `investigations/performance/README.md`.

NEXT: promote first-flip compiled RHS
