# First-flip time

This document defines the first-flip scientific quantity, its accepted claim
boundary, and its authoritative field representation. The
[first-flip pedagogy](../pedagogy/first_flip.md) owns why these data are shown
to a learner and in what order. The trusted contract originates in
[Experiment 020](../../../../experiments/physical_observables/020_first_flip_event_contract/README.md).

## Physical event

The simple-model physical state is

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2),
$$

where $\theta_1$ and $\theta_2$ are absolute link orientations measured from
the downward vertical. The solver evolves both angles as continuous lifted
coordinates. They are not wrapped modulo $2\pi$ during integration.

For each link, define its signed displacement from its initial lift:

$$
\Delta_i(t)=\theta_i(t)-\theta_i(0), \qquad i\in\{1,2\}.
$$

A first flip is the first completed net revolution by either link:

$$
\tau_{\mathrm{flip}}(x_0)
=
\inf\left\{
t>0:\max_{i\in\{1,2\}}|\Delta_i(t)|=2\pi
\right\}.
$$

This is displacement relative to the initial orientation, not accumulated path
length. It is not first passage through the upright position, wrapped angular
difference, relative elbow rotation, or a measure of chaos.

The four signed event surfaces are

$$
\phi_{i,s}(t)=s\Delta_i(t)-2\pi,
\qquad i\in\{1,2\},\quad s\in\{-1,+1\}.
$$

Each is a terminal event with positive crossing direction. The earliest
qualifying root determines the event time. Its identity records the link and
sign: `arm1-`, `arm1+`, `arm2-`, or `arm2+`. The accepted scientific scope is
transversal, numerically separated events in the equal-link simple model.
Grazing completeness and unresolved simultaneous-event attribution are not
claimed.

## Dimensionless event time

For equal link lengths $\ell_1=\ell_2=\ell$, the gravitational timescale is

$$
t_g=\sqrt{\frac{\ell}{g}},
$$

and the dimensionless representation of an observed event is

$$
\widehat{\tau}_{\mathrm{flip}}(x_0)
=\frac{\tau_{\mathrm{flip}}(x_0)}{t_g}.
$$

$\tau_{\mathrm{flip}}$ and $\widehat{\tau}_{\mathrm{flip}}$ represent the
same physical event time in different units; they are not different numerical
experiments. The current contract rejects unequal-link nondimensionalisation
rather than silently choosing a reference length.

## Bounded observation and outcomes

Every evaluation has a finite observation horizon $T_{\max}$. There are four
distinct outcomes:

- `event_observed`: a qualifying root was located and attributed;
- `right_censored`: integration completed successfully with no qualifying root
  observed by $T_{\max}$;
- `solver_failure`: integration did not complete under the solver contract;
- `invalid_integration`: integration completed but failed a scientific or
  structural validity gate.

“No flip observed by $T_{\max}$” is right-censoring. It is not evidence that
the trajectory never flips. Solver failure and invalidity are not censoring and
must not be represented as no-event outcomes.

The trusted result preserves dimensional and dimensionless event time when
observed, event state and identity, all four surface residuals, attribution,
integration endpoint, solver diagnostics, energy drift, and maximum accepted
angular increment. The trusted Python `solve_ivp` implementation remains an
independent scientific oracle. Faster production routes must reproduce this
contract and fail closed through the established recovery hierarchy.

## Authoritative field data

On the periodic initial-angle slice with zero initial angular velocities, the
authoritative persisted scalar is

$$
v(x_0)=\min\left(
\widehat{\tau}_{\mathrm{flip}}(x_0),
\widehat{T}_{\max}
\right).
$$

For a `completed_valid` cell:

- $v<\widehat{T}_{\max}$ stores an observed dimensionless first-flip time;
- $v=\widehat{T}_{\max}$ stores a right-censored observation.

Invalid and failed cells use their distinct persisted statuses and do not
contribute authoritative scalar values. The field also preserves axes,
orientation, physical and numerical definition, implementation/route
provenance, checksums, and resume state. Consequently, the authoritative data
product is not merely an image and is not interchangeable with one of its
renderings.

The equality-at-cap convention follows Experiment 020: a numerical value
coincident with the cap belongs to the censored class. An inclusive event
exactly at $T_{\max}$ cannot be recovered from the capped scalar alone; a
future need for that distinction would require an explicit scientifically
validated data contract, not reinterpretation of existing fields.

## Primitive and derived quantities

The primitive scientific measurement is the bounded trajectory outcome,
including $\tau_{\mathrm{flip}}$ and event data when a flip is observed. Its
dimensionless form is a unit transformation. The capped, status-bearing HDF5
field is the authoritative data product over the declared grid and horizon.

The following are derived representations when their required information is
already present:

- continuous or logarithmic display of observed $\widehat{\tau}_{\mathrm{flip}}$;
- discrete timescale bins, with censoring kept as a separate class;
- a threshold outcome at a supported horizon;
- comparisons among supported thresholds.

A mathematical inclusive threshold may be written

$$
F_T(x_0)=\mathbf{1}[\tau_{\mathrm{flip}}(x_0)\leq T].
$$

The current capped field's lossless operational predicate is the documented
strict “event before $H$” form

$$
F^-_H(x_0)=\mathbf{1}[v(x_0)<\widehat H],
\qquad 0<H\leq T_{\max},
$$

where $\widehat H=H/t_g$, with numerical equality assigned to the
not-observed-by-$H$ class. A derived view must state which boundary convention
it uses. It must never claim a
threshold beyond its source field's $T_{\max}$, because censored cells contain
no later event time.

Timescale bins and threshold maps do not require new dynamics when these rules
are satisfied. Finite-time stretching is not derived from first-flip data: it
is a separate tangent-space sensitivity observable with its own authoritative
field and claim boundary.

## Supported claims

First-flip time answers when a specified macroscopic event occurs, or what is
known not to have occurred by a finite horizon. It supports analysis of event
timescales and event/no-event partitions over initial conditions. It does not,
by itself, establish chaos, local instability, or a Lyapunov exponent.
