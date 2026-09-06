# First-flip teaching progression

This document owns the learner-facing sequence for first-flip material. The
[scientific reference](../science/first_flip_time.md) owns the exact observable,
event convention, censoring, and claim boundary. The
[software architecture](../architecture.md) owns how authoritative data are
computed, persisted, reused, and derived.

The [roadmap](../../../ROADMAP.md) progression is:

```text
physical event
    ↓
event timescale
    ↓
thresholded outcome map
    ↓
finite-time sensitivity as a function of observation time
```

Each representation below is warranted only when it answers a new
learner-facing question that the preceding representation did not.

## 1. Begin with the physical event

**Learner-facing question:** What counts as a flip?

A flip is one link completing a net signed revolution relative to its initial
lifted orientation. Showing or describing this event gives the learner a
macroscopic, physically legible outcome. It also establishes that a dramatic or
complicated motion is not automatically evidence of chaos.

The event alone says what happened, but not when it happened. That missing
timescale warrants the next stage.

## 2. Introduce first-flip time

**Learner-facing question:** Starting from this initial condition, when does
the first completed revolution occur?

The physical event time $\tau_{\mathrm{flip}}(x_0)$ turns a yes/no event into a
timescale. Across initial-condition space it can reveal prompt flips, delayed
flips, broad no-observation regions, and intricate boundaries. This remains a
physical event-timescale question, not a sensitivity or chaos classification.

Dimensional seconds are concrete, but they do not show how the event compares
with the system's natural gravitational timescale. That motivates a change of
units, not a new simulation.

## 3. Express the natural timescale

**Learner-facing question:** Is the event fast or slow relative to the
pendulum's natural gravitational time?

For the validated equal-link model,

$$
\widehat{\tau}_{\mathrm{flip}}
=\frac{\tau_{\mathrm{flip}}}{t_g},
\qquad
t_g=\sqrt{\frac{\ell}{g}}.
$$

$\tau_{\mathrm{flip}}$ and $\widehat{\tau}_{\mathrm{flip}}$ are the same
authoritative event time in different units. The dimensionless form makes
orders of dynamical time legible without creating another observable.

## 4. Make censoring explicit

**Learner-facing question:** What do we actually know when the event has not
appeared during the observation?

**“No flip observed by $T_{\max}$” is right-censoring, not evidence that the
trajectory never flips.** It must remain visually and conceptually distinct
from a solver failure or invalid trajectory. This stage teaches the limit of a
finite observation before any categorical map invites stronger conclusions.

Once that limit is understood, a binned view can simplify the event-time field
without hiding the censored class.

## 5. Group event times into timescale regimes

**Learner-facing question:** Which initial conditions flip on similar orders of
dynamical time?

A discrete or logarithmic timescale representation groups the authoritative
dimensionless event times into interpretable regimes and keeps “no flip
observed by $T_{\max}$” as its own class. This is a pedagogical representation
of the existing field, not a new numerical experiment. Bin boundaries are
declared presentation choices rather than new physical laws.

Bins expose broad timescale organization, but they do not directly answer
whether a flip has happened by one particular time. That warrants a threshold
view.

## 6. Threshold at a supported horizon

**Learner-facing question:** By this physically meaningful observation horizon,
which initial conditions have flipped?

A threshold map turns supported first-flip times into an outcome partition.
Conceptually it asks whether $\tau_{\mathrm{flip}}\leq T$; any operational
strict/inclusive boundary convention must be stated consistently with the
authoritative field. The map emphasizes geometry: flip-accessible and
not-observed-by-$T$ regions and their boundaries.

A threshold map may only be derived for horizons supported by the authoritative
event-time data. In particular, censored values at $T_{\max}$ cannot answer what
happens after $T_{\max}$. If a proposed horizon needs later information, it
requires a new authoritative observation rather than extrapolation or relabeling.

One threshold is a snapshot. It does not show how the partition develops with
observation time, which motivates a supported sequence.

## 7. Compare thresholds as the horizon changes

**Learner-facing question:** How does the event/no-event partition evolve as we
wait longer?

A sequence of $F_T$ views derived from the same sufficiently long authoritative
field can show regions becoming flip-accessible and boundaries appearing or
sharpening. The sequence changes the learner's question, not the underlying
dynamics. Every member must remain within the source field's supported horizon.

The evolving boundary may look intricate, but intricacy alone still does not
identify local trajectory instability. That unresolved question warrants a
separate sensitivity observable.

## 8. Compare with finite-time stretching

**Learner-facing question:** How does the geometry of a macroscopic event relate
to the local growth of perturbations over comparable observation windows?

Finite-time stretching asks how an infinitesimal perturbation grows; first-flip
time asks when a link completes a revolution. Neither quantity is a substitute
for the other. Their later comparison should make it possible to see high
stretching near event boundaries, rapid flips without especially high
stretching, or high stretching without a flip in the same horizon.

This comparison completes the intended distinction:

```text
large or complicated motion ≠ chaos
macroscopic event ≠ local trajectory instability
```

Before adding any new map or view, ask: **What new learner-facing question does
this representation answer that the previous one did not?** If it answers no
new question and uses information already present, it is a presentation choice,
not a new observable or numerical experiment.
