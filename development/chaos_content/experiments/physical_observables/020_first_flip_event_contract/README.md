# Experiment 020 — First-Flip Event Contract

**Status: ACCEPT — reference contract validated for transversal, numerically separated first-flip events.**

This directory establishes the reference calculation for a first completed link revolution in the equal-link simple double pendulum. The implementation and focused validation suite satisfy the acceptance requirements in [`PLAN.md`](PLAN.md) for transversal events whose first event is numerically separated from competing event surfaces. The contract is ready for narrow promotion into the state-space-map prototype as a scalar first-flip-time reference. True grazing contact and numerically indistinguishable multi-surface attribution remain explicit limitations rather than silently redefined events.

## Scientific question

> What precise physical event and numerical procedure provide a trustworthy reference measurement of the first completed link revolution for the equal-link simple double pendulum?

This is a physical-observable experiment. It does not estimate sensitivity, stretching, or a Lyapunov exponent. The implementation uses only the validated four-state Euler–Lagrange physical flow. It does not use tangent/JVP evolution, QR renormalisation, Candidate-A distance, the segmented Lyapunov trajectory driver, or its angular rebasing.

Successful acceptance of this experiment is the prerequisite for the first-flip event, scalar-field, and derived-threshold steps in [`development/chaos_content/prototypes/ROADMAP.md`](../../../prototypes/ROADMAP.md).

## Scientific contract

The Euler–Lagrange state is

$$
(\theta_1,\theta_2,\omega_1,\omega_2).
$$

The solver evolves the angles as continuous real-valued lifted coordinates. Define

$$
\Delta_i(t)=\theta_i(t)-\theta_i(0).
$$

The first completed link revolution is

$$
\tau_{\mathrm{flip}}
=
\inf
\left\{
t>0:
\max_{i\in\{1,2\}}|\Delta_i(t)|=2\pi
\right\}.
$$

This is the first time either lifted angular displacement reaches one complete signed revolution relative to its own initial lift.

It does not mean:

- first passage through the upright orientation;
- accumulated angular path length of $2\pi$;
- wrapped angular difference;
- relative elbow rotation;
- a threshold applied to angle modulo $2\pi$.

“First completed link revolution” is the precise scientific description. “First flip” is the shorter pedagogical name.

## Coordinate semantics

Both angles are measured in radians from the downward vertical. Both are absolute link orientations. In the production simple model,

$$
x_2=\ell_1\sin\theta_1+\ell_2\sin\theta_2,
\qquad
y_2=-\ell_1\cos\theta_1-\ell_2\cos\theta_2.
$$

Thus $\theta_2$ is not an elbow-relative angle. A $2\pi$ change in either lifted coordinate is a complete revolution of that physical link.

The reference RHS is `EulerLagrangeDynamics.flow` from the state-space prototype's validated reference module. Although that class currently lives beneath `src/lyapunov/`, this experiment uses only its four-state physical flow. It never calls `_solve_segment`, `_rebase_reference_angles`, or any augmented tangent method. This matters because angular rebasing would erase precisely the global winding history that the event measures.

## Event surfaces and identity

The implementation supplies four event functions to `scipy.integrate.solve_ivp`:

$$
\phi_{i,s}(t)
=
s\Delta_i(t)-2\pi,
\qquad
i\in\{1,2\},
\quad
s\in\{-1,+1\}.
$$

Each primary event is configured with:

- `terminal = True`;
- `direction = +1`;
- the unmodified lifted physical state;
- displacement relative to the corresponding initial lifted angle.

The earliest solver-reported root supplies the scalar time. An identity is `(arm, direction)`, rendered by the diagnostic command as `arm1+`, `arm1-`, `arm2+`, or `arm2-`.

`FirstFlipResult` retains:

- all solver-reported identities at the exact earliest solver time;
- unique winning arm/direction when applicable;
- event state;
- all four event-surface residuals at that state;
- triggering angular velocity;
- the minimum competing surface margin;
- raw per-surface event counts.

The result representation can carry multiple solver-reported identities. SciPy's event-list order is not accepted as a scientific tie-breaker. The bounded search found no useful physical near-tie candidate, and targeted nonterminal diagnostics confirmed clear separation for the closest screened case. Consequently, scalar first-event time is accepted for numerically separated events, while tied or unresolved physical attribution is not yet empirically certified.

## Observation horizon and censoring

Every call declares a finite $T_{\max}$. A successful run with no detected event is returned with status `right_censored`, meaning

$$
\tau_{\mathrm{flip}}>T_{\max}.
$$

The correct statement is “no flip observed by $T_{\max}$,” not “this trajectory never flips.”

The result status distinguishes:

- `event_observed`;
- `right_censored`;
- `solver_failure`;
- `invalid_integration`.

Censored results have no fabricated event time, dimensionless time, event state, or event identity. A later map adapter may choose a capped scalar representation, but no cap, mask, HDF5 field, or persistence decision is implemented here.

In the reference API, a root actually returned by `solve_ivp` at the endpoint is an observed physical event; a successful endpoint with no root is censored. The horizon-boundary validation showed that a horizon copied from a separately computed root can classify as censored because its recomputed root lies infinitesimally beyond the copied endpoint. The later capped field should therefore use the strict predicate $\tau_{\mathrm{flip}}<T_{\max}$: values numerically coincident with the cap belong to the capped/censored class. An explicit event-observed mask is required only if a later consumer needs to distinguish an inclusively observed event at exactly the cap from censoring.

## Dimensionless time

For this experiment only,

$$
\ell_{\mathrm{ref}}=\ell_1=\ell_2
$$

and

$$
t_g=\sqrt{\frac{\ell_{\mathrm{ref}}}{g}}.
$$

The reported dimensionless event time is

$$
\widehat{\tau}_{\mathrm{flip}}
=
\frac{\tau_{\mathrm{flip}}}{t_g}.
$$

The default baseline has $\ell_1=\ell_2=1\,\mathrm{m}$ and $g=9.81\,\mathrm{m\,s^{-2}}$, giving

$$
t_g=0.3192754284\,\mathrm{s}.
$$

`gravity_timescale` rejects unequal link lengths. This experiment does not define a nondimensionalisation convention for unequal-link systems. The `characteristic_length` used by Candidate-A tangent-space geometry is not used.

Decade-scale classes such as $1$, $10$, $10^2$, and $10^3$ in units of $t_g$ remain possible future derived views, not event-contract acceptance thresholds. The feasibility diagnosis indicates that the class below $1\,t_g$ is empty on the present zero-velocity equal-unit grid, so future bins and $T_{\max}$ must come from a coarse pilot rather than aesthetic choice.

## Reference API and result

The experiment-level entry point is:

```python
first_flip_time(
    initial_state,
    parameters=None,
    solver_spec=None,
    observation_horizon=5.0,
)
```

`initial_state` accepts an `EulerLagrangeState` or a four-component sequence in repository state order. `parameters` must retain equal link lengths. Omitting `solver_spec` selects the current starting policy:

- DOP853;
- `rtol = 1e-9`;
- `atol = 1e-11`;
- `max_step = t_g / 32`.

This policy is accepted as the reference starting policy for the validated named and screened transversal cases. Supplying `SolverSpec(max_step=None)` requests the uncapped adaptive comparison used by the validation matrix. Long-horizon pilot work must recheck the policy rather than extrapolate this bounded result.

`FirstFlipResult` exposes:

- event/censor/failure status;
- dimensional and dimensionless time;
- event identities and attribution state;
- event state, residuals, and crossing velocity;
- observation horizon and actual integration endpoint;
- solver method, tolerances, effective step cap, message, RHS/Jacobian/LU counts, and accepted endpoint count;
- maximum accepted angular increment;
- initial/event energy and maximum energy drift;
- elapsed integration wall time;
- structural validation issues.

The module also provides `run_named_trajectories()` and a bounded `--self-check`. The self-check verifies execution status, declared identities, censoring, and a smoke-level root residual tied to the solver absolute tolerance. It is not the full scientific acceptance suite.

## Energy diagnostic

The evaluator reuses the existing simple-model energy:

$$
\begin{aligned}
E={}&
\frac{1}{2}(m_1+m_2)\ell_1^2\omega_1^2
+\frac{1}{2}m_2\ell_2^2\omega_2^2 \\
&+m_2\ell_1\ell_2\omega_1\omega_2\cos(\theta_1-\theta_2) \\
&-(m_1+m_2)g\ell_1\cos\theta_1
-m_2g\ell_2\cos\theta_2.
\end{aligned}
$$

Normalized drift uses

$$
E_{\mathrm{scale}}
=
g\left[(m_1+m_2)\ell_1+m_2\ell_2\right]
$$

and

$$
\delta_E(t)=\frac{|E(t)-E(0)|}{E_{\mathrm{scale}}}.
$$

Energy is evaluated over accepted solver endpoints and at the event. It is a diagnostic, not a demand for symplectic behavior. No Experiment 020 energy acceptance gate has yet been derived.

## How to run

From the repository root, run the named implementation smoke check:

```bash
UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/first_flip_event_contract.py --self-check
```

The temporary `UV_CACHE_DIR` is useful in restricted environments and is not required in an ordinary writable development environment.

Print the complete result structures as JSON:

```bash
uv run python development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/first_flip_event_contract.py --json --self-check
```

The command writes no repository artifact. It performs five independent trajectories and prints evidence to standard output.

Run the focused scientific validation suite:

```bash
MPLCONFIGDIR=/tmp/double-pendulum-mpl XDG_CACHE_HOME=/tmp/double-pendulum-xdg UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run pytest development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/test_first_flip_event_contract.py -q
```

## Current implementation evidence

The following baseline observations were reproduced on 2026-09-04 with the default equal-unit parameters, $T_{\max}=5\,\mathrm{s}$, DOP853, `rtol = 1e-9`, `atol = 1e-11`, and `max_step = t_g/32 = 0.0099773571\,\mathrm{s}`.

| Case | $(\theta_1(0),\theta_2(0))$ | Outcome | $\tau$ / s | $\widehat{\tau}$ | $|\phi_{\mathrm{hit}}|$ | $\omega_{\mathrm{hit}}$ / rad s$^{-1}$ | max $\delta_E$ | RHS evals | Accepted points | Wall / s |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `stable_downward` | $(0^\circ,0^\circ)$ | censored | — | — | — | — | $0$ | 6074 | 507 | 0.0491 |
| `arm1_positive` | $(-150^\circ,-150^\circ)$ | `arm1+` | 2.026429865 | 6.346965 | $0$ | 2.915950 | $5.535\times10^{-12}$ | 2477 | 206 | 0.0202 |
| `arm1_negative` | $(150^\circ,150^\circ)$ | `arm1-` | 2.026429865 | 6.346965 | $0$ | -2.915950 | $5.535\times10^{-12}$ | 2477 | 206 | 0.0202 |
| `arm2_positive` | $(179^\circ,179^\circ)$ | `arm2+` | 2.399690433 | 7.516051 | $8.882\times10^{-16}$ | 4.174338 | $8.624\times10^{-11}$ | 2969 | 244 | 0.0241 |
| `arm2_negative` | $(-179^\circ,-179^\circ)$ | `arm2-` | 2.399690433 | 7.516051 | $8.882\times10^{-16}$ | -4.174338 | $8.624\times10^{-11}$ | 2969 | 244 | 0.0241 |

The measured wall times are small-run observations from one warm local process and are not map-runtime estimates.

This smoke evidence establishes only that:

- the reference implementation executes;
- the downward equilibrium reaches the horizon as a successful censored result;
- all four signed arm identities can be produced;
- the chosen positive/negative cases form numerical reflection pairs to the displayed precision;
- event roots have small surface residuals under the starting policy;
- energy drift is finite and recorded;
- terminal events reduce solver work relative to the full-horizon equilibrium case.

It does not yet establish accepted solver convergence, lift invariance, general symmetry fidelity, near-horizon stability, grazing completeness, or near-simultaneous attribution.

## Validation matrix

The focused suite compared five event trajectories under four solver policies. All used the same equal-unit physical model and $T_{\max}=5\,\mathrm{s}$.

| Policy | DOP853 `rtol` | DOP853 `atol` | Maximum step |
| --- | ---: | ---: | ---: |
| Baseline | $10^{-9}$ | $10^{-11}$ | $t_g/32$ |
| Stricter | $10^{-11}$ | $10^{-13}$ | $t_g/32$ |
| Half-step | $10^{-9}$ | $10^{-11}$ | $t_g/64$ |
| Uncapped | $10^{-9}$ | $10^{-11}$ | adaptive, no imposed cap |

The stricter run is the comparison reference. The four signed named cases and the near-horizon case retained the same event identity under every policy.

| Case | Stricter $\tau$ / s | Worst $|\Delta\tau|$ / s | Worst event-state difference | Worst max $\delta_E$ | Largest accepted angular increment / rad |
| --- | ---: | ---: | ---: | ---: | ---: |
| `arm1_positive` | 2.026429864601 | $1.793\times10^{-9}$ | $1.769\times10^{-8}$ | $1.089\times10^{-9}$ | 0.3272 |
| `arm1_negative` | 2.026429864601 | $1.793\times10^{-9}$ | $1.769\times10^{-8}$ | $1.089\times10^{-9}$ | 0.3272 |
| `arm2_positive` | 2.399690432775 | $1.172\times10^{-10}$ | $7.514\times10^{-9}$ | $1.340\times10^{-9}$ | 0.2239 |
| `arm2_negative` | 2.399690432775 | $1.172\times10^{-10}$ | $7.514\times10^{-9}$ | $1.340\times10^{-9}$ | 0.2239 |
| `near_horizon` | 4.795325801143 | $1.975\times10^{-8}$ | $1.625\times10^{-7}$ | $1.282\times10^{-9}$ | 0.2687 |

The gates were chosen after observing the complete matrix:

- event-time agreement: $5\times10^{-8}\,\mathrm{s}$, 2.5 times the worst observed difference;
- event-state agreement: $5\times10^{-7}$, 3.1 times the worst observed component difference;
- maximum normalized energy drift: $5\times10^{-9}$, 3.7 times the worst observed drift;
- event-surface residual: $10^{-10}$, ten times the baseline state absolute tolerance and far above the observed maximum of $1.776\times10^{-15}$;
- maximum accepted angular increment: $0.5\,\mathrm{rad}$, above the observed $0.3272\,\mathrm{rad}$ envelope and still well below $\pi$.

These are Experiment 020 gates for the declared cases and policies, not universal long-horizon tolerances.

## Independent root evidence

The `arm1_positive` and `arm2_positive` trajectories were reintegrated with stricter tolerances and $t_g/64$ maximum step **without event functions**. The test then located the first sign-changing accepted-step bracket independently and solved the dense-output surface with `scipy.optimize.brentq`.

| Case | Terminal root / s | Independent dense root / s | Time difference | Event-state difference | Dense residual | Bracket width / s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `arm1_positive` | 2.026429864601199 | 2.026429864601199 | 0 | 0 | 0 | 0.004988679 |
| `arm2_positive` | 2.399690432774539 | 2.399690432774539 | 0 | 0 | $8.882\times10^{-16}$ | 0.004988679 |

For `arm1_positive`, the independent run also found the later first `arm2+` surface at 2.574559699810 s, after the accepted scalar first event. No competing surface preceded either selected root.

## Lift invariance and reflection symmetry

Starting from `arm1_positive`, the suite applied lift offsets $(k_1,k_2)=(1,0)$, $(0,-1)$, and $(1,-1)$ in

$$
(\theta_1,
\theta_2)
\mapsto
(\theta_1+2k_1\pi,
\theta_2+2k_2\pi).
$$

Every shifted run retained `arm1+`. The worst event-time difference was $8.66\times10^{-14}\,\mathrm{s}$ and the worst event-state difference after removing the prescribed lift was $7.29\times10^{-13}$. Energy and triggering velocity were invariant to the same numerical scale.

The positive/negative arm-1 and arm-2 pairs had equal event times to displayed floating-point precision, the same winning arm, reversed direction and angular velocity, sign-reflected event states, and equal energy. No arm-exchange symmetry was assumed or tested.

## Censoring and horizon evidence

The stable downward equilibrium remained `right_censored` at 5 s under all four solver policies. Every run reached exactly 5 s, retained finite state, reported no event data, and had zero energy drift. The uncapped equilibrium used 98 RHS evaluations, compared with 6074 at $t_g/32$ and 12086 at $t_g/64$, demonstrating why long censored trajectories will control later cost.

The near-horizon initial state

$$
(\theta_1(0),\theta_2(0))
=
(-180^\circ,-13.846153846^\circ)
$$

produced `arm2-` at $4.795325801143\,\mathrm{s}$ under the stricter policy. A horizon $10^{-6}\,\mathrm{s}$ below that value was successfully censored; a horizon $10^{-6}\,\mathrm{s}$ above it recovered the same event. A horizon copied exactly from the separate reference run classified as censored, illustrating that numerical equality at the cap is not a stable inclusive event convention.

For later capped scalar fields, Experiment 020 recommends the strict rule

$$
\tau_{\mathrm{flip}}<T_{\max}.
$$

Numerical equality belongs to the capped/censored class. If a later scientific product needs the separate statement “a root was observed inclusively at the exact endpoint,” it should add an explicit observed-event mask rather than infer that information from the capped scalar.

## Grazing and near-simultaneous investigation

A bounded deterministic screen used the 13×13 half-open angular lattice

$$
\theta_k=-\pi+\frac{2\pi k}{13},
\qquad
k=0,\ldots,12,
$$

with zero initial angular velocities and $T_{\max}=5\,\mathrm{s}$. This was a candidate search only, not a state-space map. It produced 70 events and 99 censored results, with no solver failures.

The smallest detected absolute crossing velocity was $1.329755428\,\mathrm{rad\,s^{-1}}$ at approximately $(-152.3077^\circ,124.6154^\circ)$, an `arm1+` event at 1.759984469 s. Baseline, stricter, half-step, and uncapped runs retained the same identity; the largest time difference from the stricter run was $2.844\times10^{-9}\,\mathrm{s}$. A nonterminal diagnostic found the next distinct first surface 1.215266113 s later. This is a clearly transversal event, not a useful grazing example.

The smallest competing event-surface margin at the earliest event was 1.504575481 rad at approximately $(152.3077^\circ,96.9231^\circ)$, an `arm2-` event at 1.871734090 s. The identity and margin remained stable under all four policies, and a stricter nonterminal run found no second completed-revolution surface within 5 s. This is not a near tie.

The bounded search therefore found no trustworthy grazing or near-simultaneous physical example. The search was not expanded indefinitely. The accepted numerical claim is limited to **transversal, numerically separated events**:

- true tangential first contact may be missed by sign-change event detection;
- the scientific definition remains first contact and has not been redefined;
- solver-reported `unique` attribution is accepted only when competing surfaces are separated beyond the observed numerical uncertainty;
- exact or unresolved multi-surface attribution remains unvalidated, although the scalar earliest time remains well defined.

## Test result and experiment decision

The focused suite contains 12 scientific-contract tests covering:

- all four signed event identities;
- the complete four-policy refinement matrix;
- dimensional scaling and rejection of unequal-link use;
- individual and combined $2\pi$ lift invariance;
- reflection symmetry;
- stable censoring;
- near-horizon behavior;
- two independent dense-output roots;
- the bounded grazing/near-tie screen;
- targeted refinement and nonterminal continuation of the screen extrema.

**Verdict: ACCEPT for transversal, numerically separated first completed link revolutions in the equal-link simple model.**

The reference `first_flip_time(...)` scalar-time contract is ready for narrow promotion into `development/chaos_content/prototypes/state_space_maps/src/first_flip/`. Promotion must preserve the lifted-angle event surfaces, solver/censor/failure distinction, dimensionless equal-link scale, and strict capped-horizon recommendation. It must not claim validated grazing completeness or physical tie attribution.

## Remaining limitations

- True grazing first contact has not been demonstrated, and sign-change detection cannot guarantee its discovery.
- No physical simultaneous or numerically unresolved near-tie example was found in the bounded search; multi-identity attribution remains a result capability without empirical physical validation.
- The accepted policy has been validated only over the declared named cases, 5 s horizon, and bounded 13×13 screen. Longer pilot horizons require renewed convergence and energy checks.
- The dimensionless contract applies only when $\ell_1=\ell_2$.
- The capped-field recommendation has not been implemented in persistence code.
- No map, HDF5 field, renderer, binary threshold product, compiled evaluator, production integration, or teaching UI was created.
