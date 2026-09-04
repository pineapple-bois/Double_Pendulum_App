# Experiment 020 — First-Flip Event Contract

**Status: reference evaluator implemented; full experiment acceptance pending.**

This directory establishes the reference calculation for a first completed link revolution in the equal-link simple double pendulum. The current implementation has passed a bounded named-trajectory smoke check, including all four signed arm identities and one robust censored trajectory. It has not yet completed the refinement, lift-invariance, horizon-boundary, grazing, near-simultaneous, or focused-test campaign required by [`PLAN.md`](PLAN.md). It therefore does not yet authorize promotion into the state-space-map prototype.

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

The result representation can carry multiple identities, but the current terminal-event smoke runs do not validate near-simultaneous attribution. SciPy's event-list order is not accepted as a scientific tie-breaker. A refinement-derived tie policy, short continuation, and nonterminal diagnostic runs remain part of the pending validation work.

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

At present, a root returned by `solve_ivp` at the endpoint is an observed event; a successful endpoint with no root is censored. Whether a later capped scalar should deliberately treat exact-cap events as censored or instead retain an explicit event-observed mask remains unresolved pending the horizon-boundary experiment.

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

This is a starting reference policy, not a validated final acceptance policy. Supplying `SolverSpec(max_step=None)` requests the uncapped adaptive comparison run required later by the plan.

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

## Intended validation strategy

The subsequent focused-test and evidence task must follow `PLAN.md`. In summary it must:

1. Compare representative events under the baseline, stricter tolerances, halved maximum step, and a meaningful uncapped adaptive run.
2. Compare event time, identity, state, residual, energy, and accepted angular increments.
3. Independently bracket and refine selected roots from dense output rather than treating `t_events` as its own oracle.
4. Check invariance under adding integer multiples of $2\pi$ to either initial angle.
5. Check the reflection transformation $(\theta_1,\theta_2,0,0)\mapsto(-\theta_1,-\theta_2,0,0)$, expecting equal time, the same arm, and reversed direction.
6. Keep arm exchange out of the symmetry contract because the first arm supports both masses.
7. Run horizons below, above, and numerically close to a converged event time.
8. Inspect event velocities and dense local surfaces for suspected grazing contacts.
9. Investigate near-simultaneous candidates using all surface residuals, refinement, and short nonterminal continuation.
10. Derive numerical acceptance and tie scales from the resulting convergence evidence rather than setting them after inspecting a desired result.

The exact upward equilibrium is not the primary no-event reference because it is mathematically stationary but numerically and physically unstable.

## Unresolved questions and limitations

- The starting DOP853 tolerances and $t_g/32$ step cap have not yet been accepted for this observable.
- The smoke suite has not been rerun under the full refinement matrix.
- The terminal event detector is naturally reliable for transversal sign-changing roots; true tangential first contact may be missed without additional dense local analysis.
- No grazing candidate has yet been established.
- No physical near-simultaneous candidate or refinement-derived tie tolerance has yet been established.
- The current `unique` attribution describes the solver-reported earliest terminal surface; it is not yet a proof that no numerically indistinguishable competing surface exists.
- Lift invariance has not yet been exercised by the formal experiment suite.
- Exact-horizon behavior and later capped-field semantics remain open.
- The accepted domain is the equal-link simple model only.
- The timing evidence is insufficient to choose a coarse-pilot horizon or estimate a map cost.
- No map, persistence schema, renderer, binary threshold product, compiled evaluator, production integration, or teaching UI has been created.

## Current conclusion

The implementation is usable as the Experiment 020 reference evaluator and named-case harness. Its current evidence supports proceeding to the focused validation/test deliverable described in `PLAN.md`.

The experiment itself remains **unaccepted**, and promotion into `development/chaos_content/prototypes/state_space_maps/src/first_flip/` remains closed until the full validation campaign produces an explicit verdict.
