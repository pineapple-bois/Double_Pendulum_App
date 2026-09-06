# First-flip logarithmic-class convergence

## Decision in brief

Neither an unqualified categorical field through $\widehat H=1000$ nor one
through $\widehat H=10000$ is scientifically defensible from the tested
single-policy primitive. Exact first-event time is stable for only 8 of 17
cases in which all policies observe a flip. Coarsening helps substantially, but
does not remove the numerical dependence: 24/26 selected cases have a stable
class at $\widehat H=1000$, while 22/26 do at $\widehat H=10000$.

The decisive failures are structured, not gate failures. A reflection pair
known to be chaotic crosses the $1000$ boundary under trusted-policy
refinement. Two cases only $0.0074378$ J above the rigorous simple-model energy
barrier disagree between a $1000$–$10000$ event and censoring at $10000$. All
78 integrations pass the existing energy, accepted-step, event-residual,
solver-success, and attribution gates.

The next authoritative production artifact should therefore remain the
continuous, event-attributed $\widehat\tau_{\mathrm{flip}}$ field capped at
$\widehat H=100$, with separate finite-horizon censoring and rigorous
energy-inaccessibility. A later long-horizon categorical product would need a
distinct, model-specific numerical provenance and an explicit
`NUMERICALLY_UNRESOLVED` mask based on more than one trusted policy. It must be
derived from—not silently substituted for—the first-flip-time primitive.

## Contract and case selection

The physical contract is unchanged: equal links and unit masses, $g=9.81$,
zero initial angular velocities, lifted absolute angles, and the first terminal
surface

$$
|\theta_i(t)-\theta_i(0)|=2\pi.
$$

The gravity time is $t_g=\sqrt{1/9.81}=0.3192754284$ s. Thus the two decision
horizons are:

| Dimensionless horizon | Physical horizon |
|---:|---:|
| $1000$ | 319.275428 s |
| $10000$ | 3192.754284 s |

The deterministic 26-case list is recorded in
[`selected_cases.json`](selected_cases.json). It is selected from the previous
128×128 half-open periodic grid, whose NPZ checksum is pinned in that file:

- four early controls covering both arms, signs, and reflection;
- six probes around/interior to the 10 and 100 boundaries;
- four probes within the 100–1000 decade;
- the known $\widehat H=1000$ disagreement and its exact reflection;
- one representative energy-accessible $\widehat H=1000$ survivor from each
  open angle quadrant;
- two accessible and two inaccessible cells straddling $E=-g$;
- the downward equilibrium and a non-equilibrium inaccessible oscillation.

There is no $\widehat\tau<1$ control because the previous 128×128 evidence
contained no flip in that interval. No new field scan was performed.

For the equal-link unit simple model, the earlier derivation gives

$$
V=-2g\cos\theta_1-g\cos\theta_2,
\qquad E_0=V(\theta_1(0),\theta_2(0)),
$$

and any first revolution requires $E_0\geq -g$. Therefore $E_0<-g$ is a
rigorous necessary-condition failure: those four selected controls are
provably unable to flip and are kept separate from energy-accessible
right-censoring. Equality remains accessible. The criterion is necessary, not
sufficient, and is specific to this simple model and zero-velocity slice.

## Trusted numerical policies

All policies use the trusted symbolic Euler–Lagrange right-hand side and
SciPy's independent terminal-event `solve_ivp` execution. Refinement targets
the policy dimensions that directly affect late event detection; an unrelated
method was not added merely as nominal solver diversity.

| Policy | Method | `rtol` | `atol` | maximum step |
|---|---|---:|---:|---:|
| baseline | DOP853 | $10^{-9}$ | $10^{-11}$ | $t_g/32$ |
| strict | DOP853 | $10^{-11}$ | $10^{-13}$ | $t_g/32$ |
| strict-half-step | DOP853 | $10^{-11}$ | $10^{-13}$ | $t_g/64$ |

Each case runs independently to its first event or $\widehat H=10000$.
Dynamics, event definition, strict cap, censoring, event attribution,
diagnostics, and existing gates are unchanged. The investigation asserts that
every policy/horizon is rejected by the production native route's exact-$T=5$
allowlist. Production dispatch and eligibility were not modified.

The convergence hierarchy is:

1. `EXACT_TIME_STABLE`: every policy observes the same logarithmic class and
   the maximum physical event-time spread is at most $5\times10^{-8}$ s.
2. `DECADE_STABLE`: every policy returns the same event-decade, separate
   energy-inaccessible class, or separate finite-horizon-censored class.
3. `HORIZON_OUTCOME_STABLE`: policies agree only on flip versus no flip by the
   stated horizon.
4. `NUMERICALLY_UNRESOLVED`: a gate fails, or policies disagree on the proposed
   logarithmic representation. It can coexist with final-horizon outcome
   agreement when only the decade differs.

Arm and signed event-surface agreement are assessed separately from this
hierarchy.

## Results

At $\widehat H=1000$, 24/26 cases (92.31%) have both stable log class and stable
flip/no-flip outcome. At $\widehat H=10000$, 22/26 (84.62%) have stable class,
while 24/26 (92.31%) retain stable flip/no-flip outcome. The first disagreement
appears at the $1000$ class/horizon boundary.

Across the full cap:

- exact time is stable for 8/26 cases, or 8/17 (47.06%) of the cases observed
  by all policies;
- logarithmic class is stable for 22/26 (84.62%);
- flip/no-flip outcome is stable for 24/26 (92.31%);
- first arm agrees for 16/17 (94.12%) all-observed cases;
- signed event surface agrees for 13/17 (76.47%) all-observed cases;
- four cases are unresolved for the learner-facing logarithmic product.

The exact-time failures range from a $7.40\times10^{-7}$ s spread for the
event at $\widehat\tau\approx99.94$ to 1038.99 s for the known disagreement
pair. The former is far too small to change its decade but exceeds the existing
$5\times10^{-8}$ s equivalence gate; the latter changes the learner-facing
class. The selected-set fractions below are diagnostics over deliberately
stressful controls, not estimates of unresolved field area.

`C` below means energy-accessible censoring at $10000$; `EI` means rigorous
energy-inaccessibility. Times are dimensionless. A stable category does not
claim that the underlying late trajectory is stable.

| Case | baseline / strict / strict-half-step $\widehat\tau$ | Strongest evidence | Arm | Sign |
|---|---|---|:---:|:---:|
| `early_arm1_positive` | 6.34696 / 6.34696 / 6.34696 | EXACT_TIME_STABLE | yes | yes |
| `early_arm1_negative` | 6.34696 / 6.34696 / 6.34696 | EXACT_TIME_STABLE | yes | yes |
| `early_arm2_positive` | 7.51605 / 7.51605 / 7.51605 | EXACT_TIME_STABLE | yes | yes |
| `early_arm2_negative` | 7.51605 / 7.51605 / 7.51605 | EXACT_TIME_STABLE | yes | yes |
| `decade_10_below` | 9.98839 / 9.98839 / 9.98839 | EXACT_TIME_STABLE | yes | yes |
| `decade_10_above` | 10.0130 / 10.0130 / 10.0130 | EXACT_TIME_STABLE | yes | yes |
| `decade_10_100_mid30` | 29.9491 / 29.9491 / 29.9491 | EXACT_TIME_STABLE | yes | yes |
| `decade_10_100_mid60` | 59.9724 / 59.9724 / 59.9724 | EXACT_TIME_STABLE | yes | yes |
| `decade_100_below` | 99.9372 / 99.9372 / 99.9372 | DECADE_STABLE | yes | yes |
| `decade_100_below_reflected` | 99.9372 / 99.9372 / 99.9372 | DECADE_STABLE | yes | yes |
| `decade_100_above` | 100.520 / 100.520 / 100.520 | DECADE_STABLE | yes | yes |
| `decade_100_1000_mid150` | 150.126 / 150.089 / 150.090 | DECADE_STABLE | yes | yes |
| `decade_100_1000_mid300` | 322.415 / 331.665 / 487.497 | DECADE_STABLE | yes | **no** |
| `decade_100_1000_mid700` | 792.748 / 694.539 / 699.224 | DECADE_STABLE | **no** | yes |
| `known_h1000_disagreement` | 595.472 / 3849.69 / 905.015 | HORIZON_OUTCOME_STABLE; **unresolved class** | yes | **no** |
| `known_h1000_disagreement_reflected` | 595.472 / 3849.69 / 905.015 | HORIZON_OUTCOME_STABLE; **unresolved class** | yes | **no** |
| `h1000_survivor_quadrant_pp` | C / C / C | DECADE_STABLE | n/a | n/a |
| `h1000_survivor_quadrant_np` | C / C / C | DECADE_STABLE | n/a | n/a |
| `h1000_survivor_quadrant_nn` | C / C / C | DECADE_STABLE | n/a | n/a |
| `h1000_survivor_quadrant_pn` | 506.902 / 957.433 / 864.837 | DECADE_STABLE | yes | **no** |
| `energy_boundary_accessible_event` | 1192.07 / C / C | **NUMERICALLY_UNRESOLVED** | n/a | n/a |
| `energy_boundary_accessible_survivor` | C / C / 6548.09 | **NUMERICALLY_UNRESOLVED** | n/a | n/a |
| `energy_boundary_inaccessible` | EI / EI / EI | DECADE_STABLE | n/a | n/a |
| `energy_boundary_inaccessible_reflected` | EI / EI / EI | DECADE_STABLE | n/a | n/a |
| `energy_inaccessible_equilibrium` | EI / EI / EI | DECADE_STABLE | n/a | n/a |
| `energy_inaccessible_oscillation` | EI / EI / EI | DECADE_STABLE | n/a | n/a |

The known pair is the earliest pedagogical failure: baseline and half-step put
the event in 100–1000, while strict puts it in 1000–10000. All policies still
observe a flip by $10000$, agree on arm 2, and disagree on sign. Exact
reflection preserves each policy's event time and arm while reversing sign,
which supports deterministic symmetry without resolving the trajectory-policy
dependence.

The two barely accessible cases are the stronger $H=10000$ failure. One policy
alone observes a late event for each case (1192.07 and 6548.09 respectively),
so policies disagree even about flip/no-flip by the cap. The inaccessible
neighbors, only $0.0006191$ J below the barrier, remain rigorously classified
and censored under all policies. Disagreement therefore clusters in a known
chaotic reflection pair and immediately above the energy boundary; it does not
cluster at the deliberately sampled 10 or 100 time-bin boundaries. Three of
the four quadrant survivor representatives remain energy-accessible and
censored under all policies through $10000$.

The [diagnostic matrix](evidence/first_flip_log_class_convergence.png) is the
only visualization. It exposes policy-wise class changes without suggesting a
continuous field was computed.

## Numerical quality and cost

| Policy | Events / censored | Summed evaluation time | RHS evaluations | max energy drift | max event residual | max accepted angular increment |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 18 / 8 | 329.52 s | 32,484,538 | $2.20\times10^{-9}$ | $1.23\times10^{-13}$ | 0.1154 rad |
| strict | 17 / 9 | 396.57 s | 39,369,199 | $2.80\times10^{-10}$ | $1.94\times10^{-13}$ | 0.0965 rad |
| strict-half-step | 18 / 8 | 700.03 s | 69,886,918 | $4.61\times10^{-12}$ | $1.67\times10^{-13}$ | 0.0577 rad |

The four-worker outer wall time was 361.84 s (6.03 min); summed evaluation time
was 1426.12 s because evaluations ran in parallel. All 78 results are valid.
Better conserved energy and smaller accepted increments do not select a unique
late chaotic trajectory or class, so choosing the strictest trace as “truth”
would hide the result rather than resolve it.

## Production and roadmap recommendation

Answers to the production questions are:

1. A blanket logarithmic map through $H=1000$ is **not yet defensible**: the
   known reflection pair changes both the flip-by-$1000$ outcome and decade.
2. A blanket map through $H=10000$ is **not defensible**: it retains that class
   disagreement and adds event-versus-censor disagreement near the energy
   boundary.
3. Direct categorical generation is reasonable only under a new consensus
   contract that preserves per-policy event/censor provenance and marks
   disagreement as numerically unresolved. It is not reasonable as a
   one-policy replacement for $\tau_{\mathrm{flip}}$.
4. Yes: at least the known reflection pair and the two barely accessible cases
   are unresolved. This bounded selection measures failure modes, not their
   field-wide area.
5. The next authoritative product remains the previously validated continuous
   $\widehat H=100$ field (31.927543 s physical). Before a long categorical
   production field, a separate bounded design should
   specify a multi-policy consensus/unresolved data contract and estimate the
   unresolved spatial population without weakening any gate.

The intended teaching sequence remains valuable but must retain its numerical
qualification:

```text
physical event
    ↓
event timescale
    ↓
logarithmic timescale representation
    ↓
thresholded outcome map
    ↓
finite-time stretching versus observation time
```

The authoritative $H=100$ primitive supports thresholds at $\widehat H=1$,
10, and 100 for the later finite-time-stretching comparison. The 1000 and
10000 thresholds should not be presented as deterministic authoritative
outcomes from a single integration policy. No finite-time stretching,
threshold renderer, Poincaré map, compound dynamics, or production field was
implemented here.

“First-flip logarithmic class” is suitable model-independent terminology. Its
field geometry, equations, energy mask, and numerical validation envelope are
model-specific. The future compound model therefore needs its own equations,
energy-accessibility derivation, and convergence study before parity can be
claimed; the simple-model $E<-g$ boundary must not be copied to it.

## Reproduction and artifacts

The executable command and artifact index are in [README.md](README.md). The
machine-readable [evidence](evidence/first_flip_log_class_convergence.json)
contains all 78 policy results, physical and numerical contracts, case-level
analysis, aggregate counts, diagnostics, cost, and checksums.

The experiment generated no production-scale field and changed no production
code.

LONG-HORIZON LOG CLASSES NUMERICALLY UNRESOLVED: trusted policies cross the H=1000 decade boundary for the known reflection pair and disagree on late event versus censoring just above the simple-model energy boundary by H=10000
