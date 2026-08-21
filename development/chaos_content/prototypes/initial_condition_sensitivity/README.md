# Initial-condition sensitivity interaction prototype

This is a self-contained Stage 1 Dash prototype for exploring one learning
question:

> How do two nearby initial states evolve, and how does the observed
> relationship depend on where the system starts?

It is an exploratory interaction surface, not a production application feature,
an accepted Stage 1 numerical contract, or a chaos detector.

The revised interaction hypothesis is:

> The learner first sees one nearby pair that stays close and one that separates,
> then chooses a point in the `(theta1, theta2)` initial-angle plane, receives a
> small disclosed perturbation, and watches what happens without being promised
> divergence.

Remaining close, gradual separation, and rapid finite-time separation are all
valid observations. The prototype exists so those experiences can inform later
observable validation and pedagogical design.

## Run it

From the repository root:

```bash
uv run python development/chaos_content/prototypes/initial_condition_sensitivity/app.py
```

Open <http://127.0.0.1:8060/>. Start with either guided example, or enter two
release angles directly. Inspect the exact nearby pair and select **Release**.

Use a different local port when needed:

```bash
uv run python development/chaos_content/prototypes/initial_condition_sensitivity/app.py --port 8061
```

Run its deterministic numerical/structure check with:

```bash
uv run python development/chaos_content/prototypes/initial_condition_sensitivity/app.py --self-check
```

## Boundary and dependencies

The prototype imports only accepted, non-Dash production mechanics from
`src/double_pendulum/`:

- `DoublePendulumLagrangian` for the simple point-mass model and its
  Euler–Lagrange integration;
- `SIMPLE_REFERENCE_SOLVER_POLICY` for an existing strict DOP853 policy;
- the accepted symbolic parameter keys used by the model.

The prototype does **not** import a production page, callback, layout, payload,
or asset. Production code does not import this directory.

Everything that turns the trajectories into this teaching interaction is local:

- `app.py` owns prototype inputs, integration, diagnostics, failure handling,
  payload construction, and Dash callbacks;
- `assets/prototype.js` owns synchronized playback and Canvas drawing from
  Python-computed positions; it does not compute pendulum physics;
- `assets/prototype.css` owns the prototype presentation.

The two Canvas modes intentionally use a small local renderer instead of
changing or coupling to the production Simulation renderer. This keeps all
bespoke glue inside the sandbox while preserving the same authority split:
Python computes physics; JavaScript only interpolates precomputed samples for
display and playback.

The Canvas renderer calculates every rod direction in screen coordinates and
insets each rod endpoint by the adjacent rendered bob radius. It draws all rods
before all bobs. This local geometry rule keeps links visually terminated at
bob boundaries in both comparison modes without changing the production Canvas
renderer or hiding the problem with oversized bobs.

The CSS locally mirrors the production application's paper and white surfaces,
charcoal and muted text, teal accent, stone/control borders, restrained corner
radii, and Helvetica-based type hierarchy. No production stylesheet is loaded
or modified.

## Interaction

Both pendulums are released from rest. The learner enters `theta1` and `theta2`
in degrees and chooses a positive perturbation magnitude from `0.000001` to
`0.1` degrees. The prototype always adds that disclosed difference to `theta2`;
internally both angular velocities are zero. The exact original and nearby
angle pair is shown immediately before release. These controls make the chosen
state a location in the `(theta1, theta2)` initial-angle plane without exposing
a larger multidimensional state editor.

Two guided examples give the comparison a pedagogical role before open input:

- **Stays close** — `(0, 120, 0, 0)` versus `(0, 120.001, 0, 0)`. The fixed-pair
  experiment accepted this as a numerically credible observation that remains
  close over 20 seconds.
- **Separates** — `(179, 179, 0, 0)` versus `(179, 179.001, 0, 0)`. Both recorded
  experiment policies produced clear finite-time separation with onset times
  differing by about `0.03 s`, and the tighter-reference integrations satisfied
  their energy criterion. The production-principal integrations did not satisfy
  the predeclared energy bound, however, and only two tolerance policies have
  been compared. This example is therefore physically promising but numerically
  unresolved: it is suitable for testing the guided interaction, not accepted
  Stage 1 evidence.

“Separates” describes what this disclosed pair does under the prototype policy;
it is not a classification of the trajectory or the system as chaotic.

**Superimposed** draws both systems at their true positions about one shared
pivot. The nearby trajectory has a thinner dashed orange treatment so close
overlap remains inspectable without applying a fake offset. **Side by side**
uses two equal canvases, the same physical scale, and one shared playback clock.

Playback supports pause/resume, reset to the disclosed initial states, replay,
and 0.5x–4x speed. Editing an input pauses the loaded run so old trajectories
are not silently presented as the newly displayed pair.

## Current numerical policy

The policy is deliberately suitable for prototype interaction, not final
Stage 1 validation:

- simple point-mass double pendulum with `l1 = l2 = m1 = m2 = 1` in SI units
  and `g = 9.81 m/s^2`;
- accepted Euler–Lagrange state convention
  `(theta1, theta2, omega1, omega2)`, with both velocities fixed to zero by this
  interaction;
- DOP853 through `SIMPLE_REFERENCE_SOLVER_POLICY` (`rtol = 1e-9`,
  `atol = 1e-11`);
- 100 Hz precomputed output for smooth interpolation in the browser;
- an adjustable 2–40 second visible interval, defaulting to 20 seconds for
  comparison with the current product and experiments;
- separate solver-success, requested-time completeness, shape, and finiteness
  checks for both integrations;
- separate maximum absolute energy-drift checks, normalized by
  `g * ((m1 + m2) * l1 + m2 * l2)`, with a prototype rejection limit of
  `1e-6` for each trajectory.

The strict existing solver policy and the local `1e-6` energy bound form a
provisional interaction screen. That bound is ten times stricter than the
regime experiment's principal-run `1e-5` bound but ten times looser than its
tighter-reference `1e-7` bound; it must not be confused with either experiment
contract. It blocks gross drift while keeping known high-excitation examples
available for UX exploration. This does not establish tolerance convergence, a
predictability horizon, or robustness of any teaching conclusion. A run that
fails any current prototype check is not sent to the renderer.

The separation trace is the absolute Cartesian distance between the two second
bobs. The teaching surface presents metres only and does not classify the
result. It draws only the history reached in playback, marks the current time,
and uses the physical upper bound `2 * (l1 + l2)` for its vertical range so that
the axes do not reveal the future run. Normalized separation remains in the
internal payload for comparison with earlier experiments.

## Deliberately provisional choices

The following are interaction hypotheses to test, not settled conventions:

- whether learners benefit from both comparison modes;
- the default `theta2 + 0.001 degrees` perturbation;
- fixing the perturbation to a positive change in `theta2`;
- the release-from-rest restriction;
- the two guided examples and their wording;
- 20 seconds as the default, the 2–40 second bounds, and the speed choices;
- 100 Hz browser output;
- second-bob Cartesian distance as the primary relationship display;
- the fixed physical vertical range of the trace;
- whether the metre readout and trace help rather than distract.

## Candidate next learning direction

The guided contrast raises a question that this prototype does not answer:

> What structure appears when sensitivity is measured across the initial-angle
> plane?

A possible learning progression is now: nearby initial states can remain close
or separate; that response depends on the chosen initial state; finite-time
sensitivity can therefore be investigated across the `(theta1, theta2)` plane;
and the resulting structure may reveal complex, possibly fractal-like boundaries
between relatively ordered and strongly sensitive regions. The last point is a
hypothesis, not evidence that any boundary in this system or measurement is
fractal.

No classification metric, grid density, colour mapping, sweep implementation,
or binary-versus-continuous quantity is prescribed here. Lyapunov methodology
also remains later work.

## Known limitations and claim boundary

- The app integrates a complete pair before playback. It cannot continue a
  loaded trajectory beyond the chosen duration.
- Canvas interpolation is visual only; diagnostics use the precomputed samples.
- The fixed `0` to `2 * (l1 + l2)` separation scale is physically interpretable
  and stable across runs, but small early differences can be visually compressed.
- A strict solver policy plus an energy bound screens individual runs, but the
  prototype does not compare a tolerance hierarchy or validate robustness of
  separation onset/classification.
- Arbitrary input is intentionally bounded to protect an exploratory local app;
  those bounds are not physical definitions.
- Accessibility, small-screen behaviour, performance across browsers, and
  production-grade error messaging have not been reviewed.

The prototype may support descriptions such as “this disclosed pair remained
close over the selected interval” or “these motions became visibly different.”
A single trajectory that looks complicated, irregular, or non-periodic is not
thereby established as chaotic. The teaching comparison concerns sensitivity
between nearby states, and even that observation does not by itself prove chaos.
The prototype must not be interpreted as proof of chaos, exponential divergence,
a Lyapunov measurement, a global state-space result, or solver-independent
long-time prediction.
