# First-flip-time field and 32×32 pilot

This document records the narrow promotion of the accepted
[Experiment 020](../../../../experiments/physical_observables/020_first_flip_event_contract/README.md)
physical observable into the state-space-map prototype and the first persisted
pilot evidence. The same runner now supports arbitrary practical resolutions
and physical horizons; this document does not choose categorical views or a
production map resolution.

## Promoted observable and scope

The physical state is ordered as

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2),
$$

where both angles are absolute link orientations measured from the downward
vertical. The field fixes $\omega_1(0)=\omega_2(0)=0$ and samples the existing
half-open periodic domain $[-\pi,\pi)\times[-\pi,\pi)$.

For continuous lifted solver angles,

$$
\Delta_i(t)=\theta_i(t)-\theta_i(0),
$$

and first flip is the first completed link revolution

$$
\tau_{\mathrm{flip}}
=
\inf\left\{
t>0:\max_{i\in\{1,2\}}|\Delta_i(t)|=2\pi
\right\}.
$$

The implementation in `../../src/first_flip/reference.py` is a direct promotion
of Experiment 020's four signed, positive-crossing terminal event surfaces. It uses
the continuous four-state `EulerLagrangeDynamics.flow`; it does not use angular
rebasing, the segmented Lyapunov driver, tangent/JVP evolution, or QR machinery.
The accepted claim remains limited to transversal, numerically separated events
in the equal-link simple model. True grazing completeness and unresolved
simultaneous attribution are not claimed.

For $\ell_1=\ell_2=\ell$, the gravitational time is

$$
t_g=\sqrt{\frac{\ell}{g}},
$$

and the observed event scalar is

$$
\widehat{\tau}_{\mathrm{flip}}
=
\frac{\tau_{\mathrm{flip}}}{t_g}.
$$

Unequal-link nondimensionalisation remains out of scope.

## Censoring and persistence contract

The existing schema is sufficient without adding a mask because the
authoritative scalar is deliberately capped:

$$
v=\min\left(\widehat{\tau}_{\mathrm{flip}},\widehat{T}_{\max}\right).
$$

On a `completed_valid` cell:

- $v<\widehat{T}_{\max}$ means a first flip was observed strictly before the
  horizon;
- $v=\widehat{T}_{\max}$ means right-censored: no flip was observed by the
  horizon.

`completed_invalid` and `execution_error` remain separate HDF5 cell states with
non-authoritative NaN values. Censoring is therefore never represented as an
error or NaN. This exact cap contract supports lossless later derivation of

$$
\mathbf{1}[\tau_{\mathrm{flip}}<H]
$$

for $0<H\leq T_{\max}$ on valid cells, and arbitrary logarithmic or categorical
views within the same horizon, without reintegration. It does not distinguish an
inclusive root numerically coincident with the cap; Experiment 020 explicitly
recommended assigning numerical equality to the censored class. An explicit
event-observed mask would be justified only if that inclusive endpoint question
becomes scientifically necessary.

The HDF5 file retains explicit axes, `[theta2_index, theta1_index]` orientation,
physical/numerical/evaluator/software provenance, route and status vocabularies,
8×8 tile bounds, checksums, attempts, timings, diagnostics, and resume state.
The JSON sidecar is a readable derivative.

## Reused architecture

`src/first_flip/field_adapter.py` supplies only the observable-specific binding.
The existing neutral machinery supplies the periodic grid, cell tasks,
four-worker spawn execution, chunksize-one dispatch, 8×8 tiling,
coordinator-owned writes, checksummed completion, fail-closed resume, and final
field validation. No parallel generation or persistence architecture and no
HDF5 schema revision were introduced.

The adapter applies Experiment 020's evidence-derived residual, energy-drift,
and accepted-angular-increment gates. Nonunique event attribution and exactly
zero crossing speed fail closed because they are outside the accepted scope.
The pilot records the minimum observed crossing speed and competing-surface
margin as diagnostics; those extrema are evidence for follow-up, not new grazing
or tie tolerances.

## Pilot configuration

The pilot was created on 2026-09-04 with:

- 32 samples per axis, 1,024 cells total;
- exact half-open axes $\theta_k=-\pi+2\pi k/32$;
- equal-unit parameters $m_1=m_2=1\,\mathrm{kg}$,
  $\ell_1=\ell_2=1\,\mathrm{m}$, and $g=9.81\,\mathrm{m\,s^{-2}}$;
- $T_{\max}=5\,\mathrm{s}$ and
  $\widehat{T}_{\max}=15.6604597634$;
- DOP853 with `rtol=1e-9`, `atol=1e-11`, and
  `max_step=t_g/32=0.00997735714 s`;
- sixteen 8×8 work units and four spawn workers.

The 5 s cap is deliberately the validated Experiment 020 horizon, not a final
pedagogical choice. The 32×32 resolution is enough to exercise multiple real
tiles and reveal coarse spatial/cost structure while remaining far below a
512×512 calculation.

## Pilot evidence

| Quantity | Result |
| --- | ---: |
| Observed first flips | 450 (43.9453%) |
| Right-censored | 574 (56.0547%) |
| Completed-invalid | 0 |
| Execution errors | 0 |
| Observed $\tau$ minimum / median / maximum | 1.131105 / 2.374938 / 4.999728 s |
| Observed $\widehat{\tau}$ minimum / median / maximum | 3.542725 / 7.438523 / 15.659608 |
| Summed RHS evaluations | 4,945,310 |
| Per-cell RHS evaluations minimum / median-of-tile-medians / maximum | 1,385 / 5,409.5 / 6,158 |
| Per-cell integration wall minimum / median-of-tile-medians / maximum | 0.0128 / 0.0548 / 0.1484 s |
| Maximum event-surface residual | $1.07\times10^{-14}$ |
| Maximum normalized energy drift | $3.58\times10^{-10}$ |
| Maximum accepted angular increment | 0.1354 rad |
| Create-run wall time | 17.526 s |
| Full operation including stricter spot checks | 20.143 s |
| Generation throughput | 58.43 cells/s |
| Tile evaluation time minimum / median / maximum | 0.480 / 0.863 / 1.099 s |
| Maximum/median tile-time ratio | 1.273 |
| Minimum detected event crossing speed | 0.123263 rad s$^{-1}$ |
| Minimum competing-surface margin | 0.279336 rad |

Ten events occurred within the final 0.1 s before the cap, so horizon-boundary
classification is already relevant at this coarse resolution. The field is not
spatially uniform: a central three-column band around $\theta_1(0)=0$ was fully
censored, while the observed/censored boundary crossed many neighboring cells.
The sign-reflected capped field agreed to a maximum absolute dimensionless
difference of $7.80\times10^{-10}$, consistent with the accepted reflection
symmetry and numerical integration error.

The reported per-cell medians are medians of the sixteen persisted tile
medians; the schema deliberately does not retain every valid cell diagnostic.
All sixteen tiles completed on their first attempt. The slowest tile took 1.27
times the median, which is visible but does not yet indicate severe straggler
behavior. Censored trajectories generally integrate to the full horizon, while
observed trajectories terminate early; the nonuniform tile timings are therefore
expected. The create-run wall time includes about 3.85 s of worker/RHS setup
and 0.35 s of shutdown, so this pilot is not a basis for extrapolating a 512×512
runtime from throughput alone.

The runner then compared the mechanically selected index set
$\{0,16,31\}\times\{0,16,31\}$ against stricter `rtol=1e-11`, `atol=1e-13`
integrations. All nine classifications agreed: four observed events and five
censored trajectories. The largest event-time difference was
$2.72\times10^{-11}\,\mathrm{s}$, well inside Experiment 020's
$5\times10^{-8}\,\mathrm{s}$ convergence gate. A checksum-valid resume skipped
all 1,024 cells and left the persisted values unchanged.

The minimum crossing speed of $0.123263\,\mathrm{rad\,s^{-1}}$ is substantially
below the minimum found by Experiment 020's 13×13 screen. It is nonzero and the
cell passed the established residual, energy, and step gates, but the pilot has
not performed local dense-output refinement of that extremal cell. Accordingly,
the persisted field is accepted as a pilot of the validated transversal method,
not as new evidence that true grazing detection is solved.

## Artifacts and recommendation

The reusable operational runner is:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_first_flip_periodic_field \
  --samples-per-axis N \
  --observation-horizon-seconds T \
  --create
```

Its default HDF5/JSON stem contains both `N` and physical `T`, and `--output`
may select an explicit alternative. A matching `--resume` invocation is
fail-closed if resolution, horizon, axes, numerical policy, or provenance do
not match the existing field.

Authoritative field:

```text
development/chaos_content/prototypes/state_space_maps/outputs/first_flip_pilot/first_flip_field_32_T5s.h5
```

Readable manifest:

```text
development/chaos_content/prototypes/state_space_maps/outputs/first_flip_pilot/first_flip_field_32_T5s.json
```

The next concrete field-generation task should retain 32×32 resolution and run
a small horizon sweep beyond 5 s, with stricter spot checks and targeted
refinement of the lowest-crossing-speed cells. That evidence should choose a
useful cap before increasing resolution. Final logarithmic bins, binary
products and 512×512 generation remain premature. The existing renderer can
display any completed first-flip field with observed dimensionless times and a
separate “no flip observed by $T_{\max}$” censored class.
