# Lyapunov Experiments 003–005 Audit

## Scope

This review audits the dependency chain

$$
\text{state representation}
\rightarrow
\text{state difference}
\rightarrow
\text{scaled norm}
\rightarrow
\text{locality}
\rightarrow
\text{shadow integration}
\rightarrow
\text{renormalisation}
\rightarrow
\text{growth accumulation}
\rightarrow
\text{convergence diagnostics}
$$

across Experiments 003, 004, and 005. It distinguishes four kinds of evidence:

- **Observed code behaviour**: direct inspection of the implementation and tests.
- **Recorded numerical evidence**: the accepted `summary.json`, `manifest.json`, and cycle records.
- **Targeted numerical diagnostics**: read-only or in-memory reproductions performed for this audit.
- **Mathematical inference**: conclusions that follow from those observations but are not themselves direct code facts.

No experiment implementation or accepted experiment README was changed. The audit created no persistent diagnostic script.

## Executive finding

### Is Experiment 005's negative result trustworthy?

**Not trustworthy because of identified defect.**

The narrow statement that the original Experiment 005 run failed its predeclared checks is reproducible. The stronger interpretation—that this failure is a trustworthy property of the finite nearby-trajectory renormalisation method—is not supported.

The Candidate-A reset map, physical reconstruction, cycle growth factor, signed logarithmic accumulation, time normalization, and reference/shadow ownership are implemented correctly. Independent recomputation from `cycles.json` found no off-by-one, sign, scaling, denominator, skipped-cycle, or state-chain error.

The rejection is nevertheless contaminated by a material numerical-coordinate/protocol defect:

1. The integrator receives increasingly large lifted angle representatives. `solve_ivp` applies relative error control to those representatives, although states differing by $2\pi n$ are physically equivalent. The effective angular error scale therefore depends on winding history rather than only on the physical state.
2. Shadow segments are restarted at every reset without a `max_step` bound. A targeted reproduction of the rejected `0.125\ \mathrm{s}` cycle reduced normalized energy drift from `2.27188e-6` to `5.60668e-11` solely by setting `max_step=0.01 s`; no dynamics, state, tolerance, reset, or energy formula changed.
3. An in-memory `max_step=0.01 s` baseline/strict comparison reduced the reported final-rate discrepancy from `24.21%` to `1.99%` (`0.918473` versus `0.936793 s^-1`). This still misses the original `1%` threshold and does not establish convergence, but it proves that the headline `24.21%` anomaly is materially protocol-dependent.
4. The `10^{-6}` reset rejection is an avoidable loss of precision from adding and subtracting a tiny local angle at lifted representatives as large as `128.894 rad`. Rebasing the same reference angles to a principal local chart reduced the failed direction error from `1.34013e-8` to `1.08284e-10`.

Accordingly, Experiment 005 does establish that **the present numerical protocol has not produced a stable accepted rate**. It does not establish that the finite-shadow method itself is intrinsically unable to do so. Repair and a controlled rerun are required before choosing between further finite-shadow work and tangent/variational dynamics.

## Experiment chain reviewed

| Stage | Repository evidence | Role in the chain | Audit result |
| --- | --- | --- | --- |
| Experiment 003 | `foundations/003_lyapunov_distance_contract/README.md`; `lyapunov_distance_investigation.py`; its tests; `outputs/lyapunov_distance_contract/baseline/{summary,manifest}.json` | Defines the EL state difference, Candidate A, Candidate B, scaling metadata, and locality evidence. | Foundations are internally consistent. |
| Experiment 004 | `foundations/004_finite_time_exponential_growth/README.md`; `finite_time_exponential_growth.py`; its tests; `outputs/finite_time_exponential_growth/baseline/{summary,manifest}.json` | Tests the unrenormalised local prefix and finite-window inference rule. | Rejection of the predeclared exponential interval remains valid. |
| Experiment 005 | `foundations/005_renormalised_local_stretching/README.md`; `renormalised_local_stretching.py`; its tests; `outputs/renormalised_local_stretching/baseline/{summary,manifest,cycles}.json` | Implements repeated Candidate-A resets and convergence checks. | Algebraic algorithm is correct; numerical protocol is materially defective. |
| Production EL model | `src/double_pendulum/models/initial_conditions.py`; `lagrangian.py`; `math/functions.py`; `solver_policy.py` | Defines the actual state order, flow, angle kinematics, and `solve_ivp` policy. | State/kinematics match the experiments; solver policy has no step-size control. |

## Mathematical contract audit

### State and angle topology

**Observed code behaviour.** The solver state is exactly

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2).
$$

This is declared by `LAGRANGIAN_STATE_VARIABLE_NAMES` and `LAGRANGIAN_SOLVER_STATE_CONVENTION` in `src/double_pendulum/models/initial_conditions.py:6-11`, used by `DoublePendulumLagrangian._system` in `src/double_pendulum/models/lagrangian.py:128-136`, and repeated in all three experiment summaries under `configuration.state_order`.

All three experiments compute `nearby - reference`, wrap only the first two components, and leave velocity differences ordinary. Experiment 003's `wrap_angle_difference` and `wrapped_el_difference` are at `lyapunov_distance_investigation.py:70-86`; Experiment 004's copies are at `finite_time_exponential_growth.py:87-90,135-139`; Experiment 005's are at `renormalised_local_stretching.py:90-102`.

The wrap maps to $(-\pi,\pi]$ and maps both exact endpoint representatives to $+\pi$. Experiment 003 tests exact $\pm\pi$ and $\pm3\pi$ inputs and physically identical cross-boundary states in `test_lyapunov_distance_investigation.py:18-34`. Experiment 005 tests reset equivariance for modest representatives shifted by $2\pi$ in `test_renormalised_local_stretching.py:56-75`.

**Finding: No defect.** Wrapped subtraction is deterministic for the tested boundary values and is consistent across the chain. In Experiment 005 the largest accepted baseline pre-reset Candidate-A norm is only `1.65142e-4`, so local angular differences are orders of magnitude below the $\pi$ branch cut. No recorded accepted cycle is plausibly affected by a wrapping branch switch.

**Limitation.** Deterministic topology handling does not make subtraction equally well-conditioned for all lifted representatives. That separate precision defect is addressed under “Reset-magnitude floor.”

### Candidate-A scaling

Experiment 003 implements

$$
q=(\Delta\theta_1,\Delta\theta_2,T_c\Delta\omega_1,T_c\Delta\omega_2),
\qquad d_A=\lVert q\rVert_2
$$

in `candidate_a_distance` at `lyapunov_distance_investigation.py:93-101`. Experiment 005 separates the forward and inverse maps cleanly:

- `scaled_el_vector` multiplies only velocity components by $T_c$ (`renormalised_local_stretching.py:105-110`);
- `physical_el_vector` divides only velocity components by $T_c$ (`:113-118`);
- `candidate_a_distance` takes the norm only after scaling (`:121-124`);
- `normalized_reset` normalizes in scaled coordinates and applies the inverse map once (`:127-142`).

The metadata values match the calculation: $L_c=1\ \mathrm{m}$ and
$T_c=\sqrt{1/9.81}=0.3192754284070505\ \mathrm{s}$ appear in all three summaries and are computed by `characteristic_time`. The true $L_c=2\ \mathrm{m}$ run recomputes $T_c=\sqrt{2/9.81}$ rather than merely relabelling output.

**Finding: No defect.** $T_c$ is applied exactly once in the scaled direction and inverted exactly once during physical reconstruction. No raw mixed-units EL norm enters locality, reset, or accumulation. Experiment 005's test `test_scaled_vector_normalization_uses_characteristic_time` (`test_renormalised_local_stretching.py:19-39`) exercises all four nonzero components and the inverse map.

### Candidate-B role

`cartesian_full_state` in each experiment maps the EL state to
$(x_1,y_1,x_2,y_2,\dot x_1,\dot y_1,\dot x_2,\dot y_2)$ using the same absolute-angle kinematics as `form_lagrangian` in `src/double_pendulum/math/functions.py:49-56,71-86`. The velocity conversion is the derivative of those positions and is tested in Experiment 003 (`test_lyapunov_distance_investigation.py:37-40`). Positions are divided by $L_c$ and velocities multiplied by $T_c/L_c$ in `candidate_b_distance` (`lyapunov_distance_investigation.py:126-137`; `renormalised_local_stretching.py:209-216`).

**Finding: No defect.** Candidate B is mathematically consistent with the repository's simple EL kinematics. Its redundant constrained components are a documented convention issue, not an implementation error.

Experiment 005 correctly treats Candidate B as a diagnostic along Candidate-A-defined resets. It uses the actual previous post-reset Candidate-B norm and current pre-reset norm (`renormalised_local_stretching.py:423,461-477,540-546,566`). Its numerical agreement cannot be promoted to a Candidate-B-renormalised or norm-independent result.

### Perturbation semantics

The baseline initial scaled vector is constructed as `[0, epsilon, 0, 0]` in `run_renormalised` (`renormalised_local_stretching.py:419-423`). Because the initial direction contains no velocity component, this is initially both a physical $\theta_2$ perturbation of $\varepsilon$ radians and a Candidate-A norm of $\varepsilon$.

After the first segment, `normalized_reset` interprets `epsilon` only as the target norm of the four-component scaled direction. It never reimposes the original $\theta_2$ direction. The evolved direction is stored as `normalized_scaled_direction`, and the baseline output contains substantial signed contributions in all four components.

Code, tests, and metadata preserve this distinction:

- `test_normalized_reset_preserves_evolved_direction_not_initial_direction` at `test_renormalised_local_stretching.py:78-86`;
- `configuration.epsilon_candidate_a_norm` per run and `target_reset_candidate_a_norm` per cycle in `cycles.json`;
- `configuration.baseline_reset_candidate_a_norm` and `definitions.reset` in `summary.json`;
- the explicit wording in Experiment 005's “Direction-preserving reset map.”

**Finding: No defect.** No post-first-reset use of $\varepsilon$ as a pure angular increment was found.

## Renormalisation algorithm audit

### Reset map

The implemented map is exactly

$$
q_k^-=\operatorname{scale}(x_k^{\prime-}-x_k),
\qquad
u_k=\frac{q_k^-}{\lVert q_k^-\rVert},
\qquad
\delta x_k^+=\operatorname{scale}^{-1}(\varepsilon u_k),
$$

followed by

$$
x_k^{\prime+}=x_k+\delta x_k^+.
$$

The code path is `wrapped_el_difference` $\rightarrow$ `normalized_reset` $\rightarrow$ `reconstruct_shadow_state` at `renormalised_local_stretching.py:450-476`. It uses the current `reference_end`, not the original state, stale shadow data, or the previous reference boundary. Only the shadow is assigned `post_reset_state` at `:562-566`; the reference state array is never altered.

There is no sign loss, component reorder, physical-coordinate normalization, or reset toward the original direction. Angular wrapping occurs during local subtraction after integration and during achieved-reset verification; reconstruction adds the small signed physical angle components around the current reference representative.

### Direction preservation

For every detailed cycle in the stored `cycles.json`, this audit independently recomputed the scaled input norm, desired direction, achieved scaled direction, and direction error. The recomputed values match the stored pre-reset norms, growth factors, logarithms, cumulative sums, and rates exactly at binary-float precision. The largest baseline achieved-direction component error is the recorded `8.16805e-10`.

**Finding: No defect in the algebraic direction map.** The $10^{-6}$ failure is a representability/coordinate-conditioning problem after reconstruction, not a wrong direction formula.

### Physical-state reconstruction

`reconstruct_shadow_state` validates a unit scaled direction, applies the inverse $T_c$ map, and adds the result around the supplied reference (`renormalised_local_stretching.py:145-158`). `run_renormalised` then recomputes the wrapped physical difference and scaled achieved direction (`:468-476`).

Independent recomputation from the stored states found:

- exact agreement with every stored achieved Candidate-A norm;
- zero reference-chain, shadow-chain, and time-gap errors in all recorded detailed cycles;
- maximum baseline physical reconstruction discrepancy `9.11e-15`, well inside `1e-12`;
- exact use of the achieved post-reset norm as the next Candidate-A denominator.

**Finding: No wrong-reference or stale-state reconstruction defect.** The numerical conditioning of adding a tiny perturbation to a large lifted angle is a separate material defect.

### Growth accumulation

`growth_contribution` implements

$$
g_k=\frac{d_k^-}{d_{k-1}^+},
\qquad
\ell_k=\log g_k
$$

without absolute values, clipping, or contraction removal (`renormalised_local_stretching.py:161-170`). `run_renormalised` passes `previous_reset_a`, initially the achieved initial Candidate-A norm and subsequently the achieved reconstructed norm (`:422,456,565`).

The cumulative values are updated only after the current cycle quantities are computed, divided by the global cycle end time, and committed to algorithm state only if every cycle check passes (`:487-566`). Rejected cycles are stored for evidence but excluded from `logs_a`, final rates, and block rates (`:579-590,676-691`).

**Finding: No defect.** Independent full-cycle recomputation found zero discrepancies in `pre_reset_candidate_a_norm`, `growth_factor_candidate_a`, `log_growth_candidate_a`, `cumulative_log_candidate_a`, or `cumulative_rate_candidate_a_per_second`. All `99` baseline contractions enter the `80 s` sum. Timestamps are integer-index-generated, monotonic, contiguous, and have no omitted or duplicated interval.

One minor diagnostic-policy ambiguity remains: `relative_difference(reference, comparison)` divides by its first argument (`renormalised_local_stretching.py:311-314`), while the duration calls pass the later rate first (`:707-708`) and the late-block call passes the fourth-quarter rate first (`:719`). Thus the reported duration changes use the later-rate denominator. Using the earlier-rate denominator would give approximately `13.67%` and `20.98%` instead of `12.03%` and `17.34%`; the late-block discrepancy would be approximately `105.59%` instead of `51.36%`. Every affected check still fails. This is a minor documentation/diagnostic-definition issue, not a cause of the verdict.

## Numerical protocol audit

### Reference/shadow synchronization

Within each run, the reference is integrated once over the full requested duration by `solve_segment` (`renormalised_local_stretching.py:401-417`). `_reference_requested_times` inserts all cycle boundaries into a regular `0.01 s` output grid, and `_state_at_times` requires an available matching sample (`:374-388`). The reference boundary is therefore a stored `t_eval` value produced through `solve_ivp`'s interpolation machinery; the experiment does not request a persistent `dense_output` object, re-integrate each reference segment, or restart the reference.

The shadow is integrated segment by segment from the prior accepted `post_reset_state` on `np.linspace(start_time,end_time,11)` (`:429-448,562-566`). Both endpoints are included. Only the endpoint is used for stretching, so duplicated output of a boundary does not duplicate elapsed dynamics or accumulation.

**Finding: No structural synchronization defect.** Reference and shadow values are compared at identical requested physical times. The stored cycle chains have zero gaps and exact state hand-off.

**Numerical limitation.** Reference and shadow are separate adaptive integrations and do not share internal steps or local error. Their subtraction is therefore a subtraction of two independently approximate states. This is not necessarily invalid for a resolved finite difference, but it becomes poorly conditioned when the requested perturbation approaches their independent state error. Experiment 003's early three-magnitude collapse establishes that this was not dominant through `1.29 s`; it does not establish the same over repeated long-time resets.

Tolerance changes also change the reference integration itself. They do not merely ask two shadow solvers to follow one fixed numerical reference.

### Solver restarts and angle-coordinate error control

`solve_segment` calls `solve_ivp` with only `method`, `rtol`, and `atol` from `SolverPolicy` (`renormalised_local_stretching.py:268-280`; `src/double_pendulum/models/solver_policy.py:14-22`). No `max_step` or componentwise tolerance policy is defined. Every shadow segment restarts DOP853, so its initial step selection and adaptive history are reset every $\tau_r$.

The locked environment uses SciPy `1.18.0` (`uv.lock:580-581`). In that implementation, `scipy.integrate._ivp.rk.RungeKutta._step_impl` forms the component scale as `atol + maximum(abs(y), abs(y_new))*rtol`; `RungeKutta.__init__` defaults `max_step` to infinity and selects a new initial step for each new solver instance. These are the specific library behaviours implicated here, not a generic assumption about all integrators.

The EL right-hand side is physically periodic in the angles: repository kinematics use sines, cosines, and angle differences (`src/double_pendulum/math/functions.py:49-56,71-86`), while $\dot\theta_i=\omega_i$ (`:370-396`). Shifting either angle by an integer multiple of $2\pi$ is therefore a change of representative, not a change of physical state.

`solve_ivp` nevertheless receives lifted angles. In the baseline stored reference they reach absolute representatives of approximately `(28.16, 128.89) rad`. At `rtol=1e-9`, the angular components of the solver's nominal local error scale can therefore reach approximately `(2.82e-8, 1.29e-7)` before accounting for `atol`. These scales are about `1.3%` of the baseline $10^{-5}$ reset and `13%` of the $10^{-6}$ reset in the second angle. The same physical state expressed in a principal local chart would have an $O(10^{-9})$ angular relative-error scale.

Lifted angles do not enter the Candidate-A vector as unwrapped differences: subtraction is wrapped first. They do, however, enter both adaptive integration and the finite-state operation `reference + reset`, followed by subtraction. The intended local/history separation is therefore correct at the metric level but incomplete at the numerical-representation level.

**Major finding: numerical-coordinate/protocol defect.** The integration accuracy depends on arbitrary winding representatives. This breaks the intended equivalence between lifted history and local physical state and directly interacts with restarts, finite-difference subtraction, energy drift, and reset reconstruction.

### Tolerance sensitivity

The original baseline and strict stored references remain close early but do not remain the same numerical trajectory:

| Threshold in Candidate-A distance between stored reference states | First cycle boundary |
| --- | ---: |
| $10^{-6}$ | `6.00 s` |
| $10^{-4}$ | `15.00 s` |
| $10^{-2}$ | `21.00 s` |
| $10^{-1}$ | `22.00 s` |
| $1$ | `26.00 s` |

At `20 s`, the baseline and strict cumulative rates are still approximately `0.756196` and `0.756738 s^-1`, a difference of about `0.07%`. By `30 s`, the reference distance is approximately `0.771`, the scaled reset directions are nearly opposite in dot product (`-0.932`), and the two algorithms are following different local stretching histories. At `40 s` their cumulative rates are approximately `0.859558` and `0.718125 s^-1`; at `80 s` they are `1.039931` and `0.788167 s^-1`.

The first cycles do not show a material tolerance anomaly: the first $\ell_k$ values are `1.085621003` and `1.085621347`; at `1 s` the cumulative rates are `4.388632` and `4.388625 s^-1`; at `2 s` they are `2.747185` and `2.747276 s^-1`. The cycle-level distributions become materially different over the long histories: baseline has `221` expanding and `99` contracting cycles with mean $\ell_k=0.259983$, while strict has `199` expanding and `121` contracting cycles with mean $\ell_k=0.197042`. This is consistent with direction-preserving resets compounding small early numerical differences after the reference paths separate; it does not by itself identify an implementation error in the reset map.

Both tolerance policies use the same `t_eval` construction and the same interpolation path through `solve_segment`; neither enables an explicit `dense_output` object. Reset times align exactly. What changes is the adaptive internal step history and, eventually, the physical reference history.

The original tolerance test therefore mixes two questions:

1. Does the same local-shadow algorithm converge numerically along one reference path?
2. Do two long-time numerical reference paths, already macroscopically separated, have the same finite-time average by `80 s`?

The output cannot distinguish them. The second question may eventually have a statistical/asymptotic answer, but that is **not established from current evidence**.

A targeted in-memory diagnostic injected `max_step=0.01 s` into the existing `solve_segment` calls while retaining the original state, model, reset, durations, tolerances, and unwrapped representatives:

| Run | Original final rate / $\mathrm{s}^{-1}$ | Capped-step diagnostic / $\mathrm{s}^{-1}$ |
| --- | ---: | ---: |
| Baseline tolerance | `1.039931` | `0.918473` |
| Strict tolerance | `0.788167` | `0.936793` |
| Relative discrepancy | `24.21%` | `1.99%` |

The capped baseline reference drift was `6.63e-9` and its maximum shadow-segment drift was `2.77e-9`; the capped strict values were `1.44e-10` and `9.53e-11`. Both runs passed the existing cycle validity rules. Their reference paths still separated, so the remaining `1.99%` is not proof of convergence. The large change from `24.21%` is proof that the original headline anomaly is materially contaminated by step policy.

### Reset-interval sensitivity

The `0.125 s` run fails cycle `146`, spanning `18.125–18.25 s`, with recorded maximum segment drift `2.2718836e-6`. The energy computation is correctly based on the segment's own post-reset start state (`renormalised_local_stretching.py:479-485`); it is not divided by segment duration and does not compare across a deliberate reset. The normalization is the same fixed `29.43 J` scale used throughout.

The exact failed segment was reproduced from its stored `shadow_start_state`:

| Physically equivalent solve | Maximum normalized segment drift | Endpoint normalized energy error | `nfev` |
| --- | ---: | ---: | ---: |
| Original unrebased, uncapped baseline | `2.27188e-6` | `2.24527e-6` | `143` |
| Locally rebased angles, uncapped baseline | `8.18649e-8` | `3.54711e-9` | `194` |
| Original unrebased, `max_step=0.01 s` | `5.60668e-11` | `-1.60896e-11` | `203` |
| Original unrebased, strict tolerances | `6.22190e-12` | `-4.48948e-13` | `323` |

The unrebased uncapped endpoint differs from the rebased capped endpoint by `1.95905e-6` in Candidate-A norm despite physically equivalent initial angles. The capped unrebased and capped rebased endpoints agree to `8.65e-13`.

**Explicit finding.** The short-interval rejection is not caused by short-duration normalization, a mistaken segment-start energy, or comparison across a reset. It is a solver/restart/coordinate-conditioning artifact exposed by the missing maximum-step policy. More frequent restarts are plausibly part of the trigger, but their isolated contribution apart from angle scale and `max_step` is **not established from current evidence**.

The accepted `0.25 s` and `0.5 s` final rates remain a valid observation under the original protocol. The failed `0.125 s` run must not be used as evidence that shorter resets are intrinsically worse.

### Reset-magnitude floor

The $10^{-6}$ run fails at cycle `180` (`45.0 s`) with:

- reference angles `(25.8730, 128.8942) rad`;
- angle ULPs approximately `(3.55e-15, 2.84e-14)`;
- physical reconstruction error `1.38786e-14`;
- reset relative error `2.30302e-9`;
- unit-direction component error `1.34013e-8`.

The diagnostic is not falsely calculating the direction error: it measures a real loss when the small vector is materialized as `reference + perturbation` and then recovered by subtraction. The fixed `1e-8` relative/component threshold is stringent, but the loss is consistent with the available absolute precision of the lifted second-angle representative.

The same reconstruction around locally rebased reference angles `(0.7403,-3.0527) rad` gives:

- physical reconstruction error `2.53224e-16`;
- reset relative error `1.73350e-11`;
- unit-direction component error `1.08284e-10`.

**Explicit finding.** This is a genuine representability floor for the chosen large lifted representatives, not a fundamental floor of the physical angular state or Candidate-A norm. Local rebasing is mathematically equivalent on the angular torus and numerically better conditioned. The present representation artificially reduces the usable perturbation scale.

### Energy diagnostics

The simple-model energy formula in all three experiments matches the repository kinematics: two diagonal kinetic terms, the $m_2l_1l_2\omega_1\omega_2\cos(\theta_1-\theta_2)$ cross term, and the two gravitational potentials. Experiment 005 implements it at `renormalised_local_stretching.py:219-243`.

The diagnostics have the correct ownership:

- uninterrupted reference drift is relative to reference energy at $t=0$ (`:413-416`);
- shadow drift is relative to each segment's own post-reset start (`:479-481`);
- deliberate reset energy change is recorded separately (`:482-485`);
- the fixed normalization is $E_{\mathrm{scale}}=29.43\ \mathrm{J}$;
- the rejection threshold is `1e-7`.

**Finding: No energy-formula or energy-reference defect.** The `0.125 s` anomaly is an actual error in that numerical segment under the original solve, not an energy-metric bookkeeping error.

The metric samples only the `11` requested segment output times. A supremum between those samples is not established. More importantly, energy is one scalar invariant: two trajectories can conserve energy closely while differing in phase, winding history, local tangent direction, or finite-difference separation. The baseline's `9.11e-8` reference drift and the strict run's `8.07e-10` drift do not validate synchronization or a Lyapunov rate. Energy checks can pass while the tangent/separation calculation remains unreliable.

## Specific anomaly findings

### 24.21% tolerance discrepancy

- **Observed:** reproducible in the stored output and rerun.
- **Cause established:** the two policies no longer follow the same reference path after approximately `21–26 s`, and the result is materially altered by `max_step` control.
- **Cause not established:** whether a fully conditioned finite-shadow method would converge to one stable long-time value for this initial state.
- **Classification:** Major numerical-protocol and diagnostic-policy defect. The original discrepancy cannot be attributed solely to genuine chaotic sensitivity of the finite-shadow algorithm.

### `0.125 s` interval energy rejection

- **Observed:** cycle-local energy failure is real under the original integration.
- **Cause established:** arbitrary lifted-angle error scale plus uncontrolled segment step size; `max_step=0.01 s` removes the failure by over four orders of magnitude.
- **Excluded causes:** duration normalization, wrong energy denominator, wrong segment-start energy, and comparison across a deliberate reset.
- **Classification:** Moderate manifestation of the major numerical-protocol defect. It does not invalidate the reset algebra and does not establish interval instability.

### $10^{-6}$ reconstruction rejection

- **Observed:** achieved reset direction really exceeds the declared threshold in the lifted representation.
- **Cause established:** subtraction/reconstruction precision at large lifted angles; local rebasing improves direction error by roughly two orders of magnitude.
- **Classification:** Moderate coordinate-representation defect. It is not a fundamental perturbation-size floor.

### Long-time non-convergence

- **Observed:** the original baseline cumulative sequence `0.756196`, `0.859560`, `1.039931 s^-1`, its late blocks, and its final-quarter range fail the predeclared checks.
- **Interpretation supported:** no stable rate has been demonstrated by `80 s` under the original protocol.
- **Interpretation not supported:** the drift is an intrinsic property of the nearby-trajectory renormalisation method. The capped-step baseline gives `0.757473`, `0.811815`, `0.862573`, `0.918473 s^-1` at `20`, `40`, `60`, and `80 s`, showing materially different convergence behaviour without changing the mathematics.
- **Classification:** Inconclusive about the method; contaminated as a causal negative result.

## Defects found

| Severity | Classification | Finding | Exact evidence | Effect on verdict |
| --- | --- | --- | --- | --- |
| **Major** | Numerical-protocol / coordinate issue | Lifted angles enter componentwise relative error control even though $2\pi$-shifted states are physically equivalent. | `run_renormalised` passes lifted states at `renormalised_local_stretching.py:401-435`; `solve_segment` at `:268-280`; `SolverPolicy.solve_ivp_kwargs` at `src/double_pendulum/models/solver_policy.py:14-22`; stored angles reach `128.894 rad`. | Makes solver accuracy winding-dependent and contaminates long-time finite differences. |
| **Major** | Numerical-protocol issue | Shadow restarts have no `max_step` bound. | Same functions; failed-cycle diagnostic changes drift `2.27e-6 -> 5.61e-11`; capped tolerance discrepancy changes `24.21% -> 1.99%`. | Invalidates attribution of headline anomalies to the method alone. |
| **Major** | Diagnostic-policy issue | The tolerance comparison changes both the reference and shadow, then compares rates after references are macroscopically separated. | `run_investigation` constructs two independent `run_renormalised` calls at `renormalised_local_stretching.py:931-943`; stored reference distance exceeds `1` by `26 s`. | Confounds integrator convergence with different finite-time orbit histories. |
| **Moderate** | Coordinate-representation issue | The $10^{-6}$ floor is caused by reconstructing around large lifted angles. | `reconstruct_shadow_state` and achieved subtraction at `:145-158,468-476`; failed cycle `180`; local-rebase diagnostic. | Rejects an otherwise usable magnitude and makes the magnitude audit incomplete for avoidable reasons. |
| **Moderate** | Numerical-method manifestation | The `0.125 s` interval failure is a step/coordinate artifact, not a bad energy reference. | Energy calculation at `:479-485`; failed cycle `146`; targeted segment reproduction. | Makes interval-robustness rejection non-diagnostic about reset interval. |
| **Minor** | Diagnostic-policy / documentation issue | Relative duration/block denominators are the later rates and are not clearly declared beside the outputs. | `relative_difference` and calls at `:311-314,707-719`. | Numerical percentages change, but every conclusion is unchanged. |
| **Minor** | Test-coverage issue | Unit tests verify algebraic reset properties but not long-run $2\pi$-representative invariance, shared-reference tolerance convergence, or step control. | `test_renormalised_local_stretching.py:19-154`. | Allowed the material numerical-coordinate defect to pass all `24` local tests and self-checks. |
| **No defect** | Implementation | State order, wrapping, Candidate-A scaling/inverse, Candidate-B kinematics, perturbation semantics, reset direction, reconstruction reference, segment chain, signed logarithms, and accumulation are correct. | Functions and independent `cycles.json` recomputation cited above. | The core algebra does not require redesign before the numerical protocol is repaired. |

No Critical defect was found. No wrong equation, state-component permutation, sign loss, stale reset, skipped contraction, or elapsed-time error was found.

## What remains valid from Experiments 003–005

### Experiment 003

The following accepted findings survive:

- the EL state convention and deterministic local wrapped-angle difference;
- Candidate A as an explicit dimensionally coherent working norm under a declared $T_c$;
- Candidate B as a mathematically consistent full-state comparison embedding;
- rejection of the raw mixed-units norm and second-bob distance as a Lyapunov norm;
- the early common local regime and three-magnitude collapse through `1.29 s`;
- the distinction between wrapped local separation and lifted winding history;
- finite-time norm/scaling dependence and the non-uniqueness of the chosen norm.

The angle-error-scale defect is negligible for the initial short local interval compared with its later manifestation, and Experiment 003's strict comparison is extremely close there.

### Experiment 004

The predeclared `0.32–1.12 s` Candidate-A interval fails its linearity/residual criteria, and the endpoint audit fails. Those are direct short-time trace properties, not consequences of Experiment 005's restart implementation. The claim “no defensible common approximately exponential interval under the predeclared rule” remains valid.

Its recorded `3.72245 s^-1` value remains only a descriptive finite-window number. Candidate A/B disagreement and alternative-scaling curvature remain valid cautions.

### Experiment 005

These observations survive:

- the implemented reset algebra preserves the evolved four-component scaled direction for the accepted baseline;
- the baseline remains under the empirical local ceiling;
- contractions are retained and accumulation bookkeeping is correct;
- the uninterrupted reference and reset algorithmic shadow have the documented ownership;
- the original runs do not demonstrate convergence or a maximal Lyapunov exponent;
- the $10^{-4}$ and $10^{-5}$ original-protocol rates agree closely;
- the original `0.25 s` and `0.5 s` rates agree closely;
- the limited Candidate-B-along-A and $L_c=2\ \mathrm{m}$ observations are descriptive evidence along the Candidate-A algorithm, not norm independence.

What does not survive is attributing the failed magnitude, interval, tolerance, and long-duration checks to an intrinsic limitation of finite shadow renormalisation.

## What should not be claimed

- The `1.039931 s^-1` baseline or `0.788167 s^-1` strict value is a maximal Lyapunov exponent.
- The `24.21%` discrepancy measures only tolerance sensitivity of one otherwise fixed reference trajectory.
- The finite nearby-shadow method is intrinsically too tolerance-sensitive for this project.
- A `0.125 s` reset interval is numerically worse in principle than `0.25 s` or `0.5 s`.
- $10^{-6}$ is a floating-point floor for the physical EL perturbation or Candidate-A norm.
- Passing energy checks validates tangent direction, shadow synchronization, or exponent convergence.
- Candidate-B-along-A agreement establishes norm-independent or Candidate-B-reset convergence.
- The near-inverted reference case is numerically pathological. **Not established from current evidence.**
- Tangent/variational dynamics is already required. It is a strong later candidate, but the current finite-shadow method has not yet received a coordinate-invariant, step-controlled test.

## Assessment of the nearby-trajectory method

Independently integrating and resetting a finite shadow is not yet shown to be sufficiently well-conditioned for the next project stage. The present implementation has three coupled sources of difficulty:

1. independent reference/shadow truncation errors are subtracted to recover an $O(\varepsilon)$ quantity;
2. finite states must be reconstructed after every cycle;
3. lifted angle magnitude changes both solver error scaling and reconstruction precision.

Experiment 003 shows that finite differences work cleanly over the early local prefix. Experiment 005 shows that the algebraic resets can work for many cycles. It does not separate the method's long-time conditioning from the correctable protocol defects above.

The proper current conclusion is therefore not “finite shadows have failed,” but “finite shadows have not been tested under a numerically representation-invariant policy.”

## Tangent/variational dynamics as a later recommendation

A later formulation could evolve

$$
\dot{\delta x}=J(x(t))\,\delta x
$$

along one reference trajectory. Relative to the current implementation, this would remove or substantially reduce:

- subtraction of two independently integrated finite states;
- shadow/reference endpoint synchronization error;
- the need to materialize $\varepsilon u$ as `reference + perturbation` and recover it by subtraction;
- the reset-magnitude representability floor;
- repeated finite-state reconstruction error.

It would not automatically solve every observed problem. The reference solver would still need a coordinate-invariant error policy; integrating lifted angles with relative tolerances can affect the reference even if the perturbation equation is exact. Tangent dynamics also introduces new risks:

- correctness of all entries of the EL-flow Jacobian;
- maintaining the repository's state order and Candidate-A scaling in the tangent vector;
- differentiating a smooth local angular chart rather than the discontinuous wrap function;
- choosing and validating analytic, symbolic, automatic, or numerical differentiation;
- checking the variational result against finite differences over a short resolved interval;
- validating renormalisation, convergence, and energy/reference behaviour independently.

Tangent dynamics is mathematically cleaner for the eventual exponent calculation, but Experiment 005 does not yet justify skipping the narrower repair needed to determine whether the present method's rejection was artificial.

## Recommendation for next experiment

**Primary recommendation: 1. Repair and rerun Experiment 005.**

This is not a request to loosen thresholds, choose a favourable run, change initial conditions, or extend the duration. It is a request to make the existing numerical question invariant to physically equivalent angle representatives and to control the segment step policy before reusing the original acceptance logic.

The repair should address both parts together:

- use a local/rebased angular representation for numerical integration and reset reconstruction while retaining lifted winding only as separate history metadata; and
- declare a mechanically justified `max_step` policy for reference and shadow solves, applied equally to baseline and strict tolerances.

The tolerance comparison must also state whether it tests two independently drifting references or shadow convergence along one fixed high-accuracy reference. The latter isolates the nearby-trajectory algorithm more cleanly.

Only after this rerun should the project decide whether a narrow numerical-convergence investigation is still needed or whether tangent/variational dynamics is the justified next mathematical formulation.

## Minimal next-step contract

**Question.** After making the solver and reconstruction invariant to $2\pi$ angle-representative shifts and applying one declared step bound, do the existing baseline/strict `80 s`, `0.125 s`, and $10^{-6}$ cases still fail for dynamical rather than representational reasons?

**Minimum evidence.** Reuse the current state, Candidate-A definition, reset map, durations, tolerances, energy formula, and acceptance thresholds. Do not add initial conditions or a parameter sweep. Re-run only the baseline and strict headline cases plus the two previously rejected anomaly cases.

**Acceptance boundary.** Before interpreting rates:

1. Physically equivalent $2\pi$-shifted segment starts must give the same wrapped endpoint, achieved reset norm/direction, and energy diagnostic within the existing reconstruction/direction/energy tolerances.
2. The declared step policy must make the `0.125 s` case pass or fail reproducibly without changing the policy by case.
3. The $10^{-6}$ case must be judged in a local chart; failure may then be attributed to true finite-difference/solver resolution rather than lifted-coordinate subtraction.
4. The baseline-versus-strict rate comparison must use a clearly identified reference-path contract. The existing `1%` rate threshold should remain unchanged.

If these conditions pass and the rate still fails duration/tolerance convergence, the negative result becomes credible and tangent/variational dynamics is the next justified move. If coordinate/step invariance itself cannot be obtained, finite-shadow renormalisation should be abandoned for this project without a broad sweep.

## Diagnostics executed

The existing experiment-local tests and self-checks were rerun:

```bash
UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run pytest \
  development/chaos_content/experiments/foundations/003_lyapunov_distance_contract/test_lyapunov_distance_investigation.py \
  development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/test_finite_time_exponential_growth.py \
  development/chaos_content/experiments/foundations/005_renormalised_local_stretching/test_renormalised_local_stretching.py -q

UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python \
  development/chaos_content/experiments/foundations/003_lyapunov_distance_contract/lyapunov_distance_investigation.py --self-check

UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python \
  development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/finite_time_exponential_growth.py --self-check

UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python \
  development/chaos_content/experiments/foundations/005_renormalised_local_stretching/renormalised_local_stretching.py --max-duration 80 --self-check
```

Results: `24 passed`; all three self-checks passed and reproduced their recorded statuses.

Additional in-memory diagnostics loaded the tracked `cycles.json` and called the existing Experiment 005 functions without modifying them:

- full recomputation of reset norms, directions, physical reconstruction, growth, signed logs, cumulative sums/rates, state hand-off, and timing;
- baseline/strict reference-distance, reset-direction, cycle-log, and cumulative-rate comparison at common cycle boundaries;
- exact replay of rejected `0.125 s` cycle `146` with the original state, a physically equivalent locally rebased state, `max_step=0.01 s`, and strict tolerances;
- exact replay of the $10^{-6}$ reconstruction at cycle `180` before and after local angle rebasing;
- baseline and strict `80 s` runs with an in-memory wrapper adding `max_step=0.01 s` to every existing `solve_segment` call.

These diagnostics wrote no repository files and did not change any experiment threshold or accepted README.

## Final verdict

Experiment 005 correctly implements direction-preserving Candidate-A renormalisation and growth accumulation, but its accepted negative interpretation is contaminated by winding-dependent solver error control, uncontrolled DOP853 segment step size, avoidable lifted-angle reconstruction loss, and a tolerance comparison that follows different long-time references. The current evidence is sufficient to reject an exponent claim, but not to reject the finite nearby-trajectory method itself. Repair the numerical representation and step policy, rerun only the existing headline and anomaly cases, and move to tangent/variational dynamics only if that conditioned rerun still fails.
