# 013 Restart-Grade QR Continuation

**Status: Phase A accepted for restart-grade QR-boundary continuation under
the declared short-run protocol.**

## Question

> Can the validated Euler–Lagrange and canonical Hamiltonian tangent-QR
> calculations be serialized at a QR boundary and resumed so that a split run
> reproduces the corresponding uninterrupted run to numerical precision?

This is an infrastructure and numerical-validity experiment. It creates no
new long-time Lyapunov evidence and does not reinterpret Experiment 012.
Experiment 012's historical output remains non-resumable because it omitted
its terminal reference and post-QR tangent arrays.

## Definition

A complete restart is taken only immediately after a QR reset. Schema
`chaos_tangent_qr_boundary_restart`, version `1`, contains:

- formulation and physical initial-condition identity/metadata;
- solver-policy name, method, `rtol`, `atol`, and `max_step`;
- QR interval, elapsed time, and completed cycle count;
- cumulative componentwise `sum(log(abs(R_ii)))`;
- fixed-column, positive-diagonal, no-sorting convention identifier;
- Candidate-A EL scaling or canonical pullback-metric identifier;
- the original diagnostic energy/Hamiltonian baseline;
- locally canonical reference-state ordering and the explicit statement that
  winding is not restart state;
- Git commit and dirty-tree status when Git is available;
- Python implementation/version and NumPy/SciPy versions;
- SHA-256 hashes for the directly executed Experiment 006, 007, 011 where
  applicable, and Experiment 013 source files;
- the locally rebased four-component terminal reference state;
- the `4x4` post-QR tangent matrix expected by the next interval; and
- the four cumulative log sums.

The numeric arrays are authoritative `float64` values in an NPZ bundle. JSON
metadata records their shapes, dtypes, exact round-trippable previews, and the
NPZ SHA-256. A checkpoint manifest hashes both files.

For EL the boundary arrays are

```text
x = (theta1, theta2, omega1, omega2)
Y_EL^+ = S^-1 Q.
```

For canonical evolution they are

```text
z = (theta1, theta2, p_theta1, p_theta2)
Y_H^+ = A(z)^-1 Q.
```

Angles already occupy the accepted local `(-pi, pi]` chart and are consumed
verbatim on resume. Neither formulation carries winding state. DOP853 history
is also absent by design: every accepted `0.25 s` QR interval starts a new
`solve_ivp` invocation.

## Compatibility policy

Loading fails on malformed arrays, missing fields, schema/version mismatch,
wrong formulation, changed solver policy, changed `max_step`, changed QR
interval, state/tangent convention changes, or integrity failure.

Runtime, source-hash, or Git provenance mismatch is a hard failure by default.
An explicit `allow_provenance_mismatch=True` override may load the checkpoint,
but returns recorded warnings. This supports deliberate forensic access; it
does not certify that continuation as the same numerical implementation.

## Minimal experiment

The Phase A protocol is frozen before execution:

| Item | Value |
| --- | --- |
| Physical state | `(179°,179°,0,0)` |
| Formulations | EL Candidate-A QR; canonical pullback QR |
| Solver | DOP853, `rtol=1e-9`, `atol=1e-11` |
| `max_step` | `0.0099773571 s` |
| QR interval | `0.25 s` |
| Total duration | `1.0 s` |
| Split boundary | `0.5 s`, after cycle 2 |
| Uninterrupted cycles | 4 |
| Resumed cycles | globally numbered 3 and 4 |

For each formulation:

1. run uninterrupted from `0` to `1.0 s`;
2. run a prefix from `0` to `0.5 s`;
3. create, save, and reload a QR-boundary checkpoint;
4. resume from `0.5` to `1.0 s`; and
5. compare the split calculation with the uninterrupted cycles 3–4.

This state is an already understood validation anchor, not a new physical
case. No `640 s`, `1280 s`, or production-length integration is permitted.

## Predeclared numerical validity

The NPZ round trip must preserve all three float64 arrays with exact
`numpy.array_equal` equality. Counters, policy metadata, and provenance must
also survive unchanged.

At final `1.0 s`, and cycle-by-cycle after the split, the maximum absolute
differences in reference components, post-QR tangent components, cycle logs,
cumulative logs, and cumulative spectrum components must each be at most
`1e-13`. Final energy/Hamiltonian disagreement must be at most `1e-13 J`.
Elapsed time, final cycle count, and resumed global cycle numbers must agree
exactly. Both runs must retain their accepted QR and energy checks, and their
cumulative bookkeeping errors must remain at most the inherited `1e-12`.

The `1e-13` comparison scale is tighter than the accepted QR bookkeeping
guard and is appropriate because the split occurs at an existing solver/QR
restart boundary, binary serialization is lossless, and both paths execute
the same subsequent segment calls. It will not be relaxed after inspection.
Bitwise split-run equality is not required in advance.

## Acceptance

Phase A is accepted only if:

- the checkpoint contract is complete and validates itself;
- required float64 state survives serialization exactly;
- both EL and canonical split runs satisfy the predeclared comparisons;
- cumulative logs, elapsed time, and cycle numbering continue rather than
  restart;
- incompatible metadata is rejected and provenance overrides are explicit;
- evidence files have integrity hashes; and
- only the declared short calculations are needed.

## Findings

**Verdict: accepted.** The frozen `1.0 s` comparison completed for both
formulations. No threshold or protocol field was changed after execution.

The JSON/NPZ save-load cycle preserved the reference state, post-QR tangent
matrix, and cumulative log vector with exact `numpy.array_equal` equality.
The saved elapsed time remained `0.5 s`, the completed cycle count remained
`2`, and resumed cycles were globally numbered `3` and `4`. Policy, metric,
sign/ordering, energy-baseline, and provenance metadata were unchanged and
loaded without warnings.

The observed uninterrupted-versus-split errors were:

| Maximum absolute error | EL | canonical | Limit |
| --- | ---: | ---: | ---: |
| Terminal reference component | `0.0` | `0.0` | `1e-13` |
| Post-QR tangent component | `0.0` | `0.0` | `1e-13` |
| Cumulative log component | `0.0` | `0.0` | `1e-13` |
| Cumulative diagnostic component | `0.0 s^-1` | `0.0 s^-1` | `1e-13 s^-1` |
| Final energy/Hamiltonian | `0.0 J` | `0.0 J` | `1e-13 J` |

For both post-split cycles, the reference start/end, tangent start/pre/post QR,
cycle logs, and cumulative logs also have maximum absolute difference `0.0`.
Both uninterrupted and resumed calculations retain their inherited numerical-
validity checks, and cumulative bookkeeping error is `0.0`.

The observed zero numerical difference is stronger than the preregistered
numerical-equivalence requirement. It is reported as an implementation result
for this runtime and source provenance, not promised across changed versions.

Negative tests establish rejection of wrong formulation, solver policy,
`max_step`, QR interval, schema version, missing cumulative arrays, and invalid
reference/tangent shapes. A source-hash provenance mismatch fails by default;
the explicit override loads only with a recorded warning.

The short final fixed-column diagnostics, included only to audit accumulation,
are

```text
EL:        ( 4.707844765171036,  2.156461533501171,
            -1.993152181772131, -5.291880961515483) /s
canonical: ( 4.707844765171033,  2.156461533501170,
            -1.993152181772132, -5.291880961515481) /s
```

They are not long-time spectrum estimates.

Machine-readable evidence is stored under the ignored tree:

```text
development/chaos_content/experiments/outputs/013/
  phase_a/
```

Each formulation owns checkpoint JSON, float64 NPZ arrays, a checkpoint
manifest, and a comparison result. The root contract, summary, and SHA-256
manifest cover the complete Phase A evidence. Reproduce the short validation
with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  development/chaos_content/experiments/lyapunov_validation/013_restart_grade_qr_continuation/restart_grade_qr_continuation.py \
  --self-check
```

## Claim boundary

Acceptance may establish only:

> Exact or numerically equivalent QR-boundary continuation of the accepted
> finite-time tangent-QR machinery under the tested short-run conditions.

It will not establish longer-time Lyapunov convergence, Experiment 012
robustness, IC-1/IC-3 settling, `1280 s` sufficiency, or restart equivalence
across different code/runtime versions.

## Next experiment boundary

If accepted, a separately designed Phase B may use restart-grade
serialization in a new from-zero duration-convergence experiment for IC-1 and
IC-3. This phase does not freeze Phase B's endpoint, checkpoints, or acceptance
contract.

The remaining prerequisite is therefore scientific rather than
infrastructural: preregister the Phase B duration/checkpoint and acceptance
contract before any production-length from-zero run begins.
