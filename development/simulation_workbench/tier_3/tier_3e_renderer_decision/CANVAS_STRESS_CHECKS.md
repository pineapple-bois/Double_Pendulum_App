# Canvas Stress Checks

Tier: Phase 6 / Simulation Workbench Tier 3E
Date: 2026-05-29

## Summary

Tier 3E ran compact Canvas payload stress checks against representative model,
system, duration, and initial-condition cases.

The checks measure payload construction assumptions, not browser rendering
memory and not scientific correctness.

No full payload arrays, screenshots, HTML exports, or Plotly JSON files were
saved.

## Script

Run from the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3e_renderer_decision/canvas_stress_runner.py
```

Output:

- `tier3e_results.json`;
- compact stdout summary.

The runner records:

- model construction time;
- position precompute time;
- payload preparation time;
- sample count;
- duration;
- payload size bytes;
- approximate bytes per sample;
- warning count;
- solver success/status/message;
- state finite check;
- position finite check;
- monotonic time check;
- endpoint check;
- whether arrays were saved.

Model construction timing includes current model construction, equation loading
or lambdification when triggered, and integration. It should not be interpreted
as pure integration time.

## Stress Cases

| Case | Model | System | Initial conditions | Duration | Samples | Status |
| --- | --- | --- | --- | ---: | ---: | --- |
| `simple_lagrangian_baseline_5s` | simple | Lagrangian | `[45, -30, 0, 0]` | `5s` | `1000` | success |
| `simple_hamiltonian_nonzero_5s` | simple | Hamiltonian | `[45, -30, 10, -5]` | `5s` | `1000` | success |
| `compound_lagrangian_large_angles_10s` | compound | Lagrangian | `[120, -100, 0, 0]` | `10s` | `2000` | success |
| `compound_hamiltonian_large_velocity_10s` | compound | Hamiltonian | `[150, -130, 20, -15]` | `10s` | `2000` | success |
| `simple_lagrangian_long_20s` | simple | Lagrangian | `[120, -100, 10, -5]` | `20s` | `4000` | success |
| `compound_hamiltonian_long_20s` | compound | Hamiltonian | `[120, -100, 10, -5]` | `20s` | `4000` | success |

The 20-second cases were tested with 4000 samples. This is a useful old-style
duration stress check, not proof of long-duration numerical stability.

## Metrics Summary

| Case | Samples | Payload bytes | Bytes/sample | Model construction | Solver nfev | Finite arrays |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `simple_lagrangian_baseline_5s` | `1000` | `175430` | `175.4` | `2.0606s` | `290` | yes |
| `simple_hamiltonian_nonzero_5s` | `1000` | `137841` | `137.8` | `0.4731s` | `260` | yes |
| `compound_lagrangian_large_angles_10s` | `2000` | `347746` | `173.9` | `2.1694s` | `368` | yes |
| `compound_hamiltonian_large_velocity_10s` | `2000` | `271939` | `136.0` | `0.3792s` | `392` | yes |
| `simple_lagrangian_long_20s` | `4000` | `690847` | `172.7` | `0.0589s` | `1490` | yes |
| `compound_hamiltonian_long_20s` | `4000` | `542791` | `135.7` | `0.0430s` | `692` | yes |

Largest measured payload:

- `690847` bytes for `simple_lagrangian_long_20s`;
- `4000` samples;
- full arrays omitted from results JSON.

## Checks Passed

All six stress cases:

- constructed successfully;
- reported solver success;
- returned requested time sample count;
- produced `(sample_count, 4)` state arrays;
- produced `(4, sample_count)` position arrays;
- produced finite state arrays;
- produced finite position arrays;
- produced monotonic time arrays;
- matched requested end time.

## Hamiltonian Payload Caution

Hamiltonian runs use canonical momenta internally.

The stress runner records user-facing initial angular velocities and internal
state convention. It does not serialize Hamiltonian state slots three and four
as `omega1` and `omega2`.

If production needs Hamiltonian angular-velocity time series, Python must add an
audited velocity reconstruction. JavaScript must not infer it from momenta.

## Repeated Runs

The runner executed six sequential model/payload builds in one process. This
shows repeated payload construction works at this small workbench scale.

It does not prove browser memory behavior across long user sessions.

## Clear / Failure After Large Payload

Tier 3C.2 and Tier 3D browser checks verified clear, failure, and stale-run
cancellation behavior with workbench payloads.

Tier 3E did not rerun browser clear/failure checks against the 4000-sample
payload because the current Tier 3C preview does not expose the Tier 3E large
angle/20-second stress matrix. This should be a production promotion gate.

## Browser Resize

Tier 3C.2 implements Canvas resize/redraw behavior in the workbench renderer.

Tier 3E did not perform a new browser resize stress pass. Production promotion
should include resize checks with:

- a short successful run;
- a 20-second payload;
- stale output;
- failure/cleared states.

## Interpretation

This stress pass supports:

- Canvas payloads can be generated for representative larger-angle and
  20-second model runs;
- payload sizes are measurable and nontrivial;
- 20-second / 4000-sample payloads are below 1 MB in the current JSON shape;
- simple/compound and Lagrangian/Hamiltonian cases remain array-sane under the
  tested conditions.

This stress pass does not support:

- energy conservation claims;
- chaos diagnostics;
- long-session memory claims;
- final payload-size acceptance;
- accessibility/export adequacy;
- browser performance under every device class.

## Recommendation

Proceed with Canvas as the preferred production candidate, but keep payload
monitoring and lifecycle browser checks as hard promotion gates.

Before production acceptance, manually or automatically test the final
production renderer with at least:

- 5-second baseline payload;
- 10-second larger-angle payload;
- 20-second / 4000-sample payload;
- rapid repeated runs;
- clear after large payload;
- simulated or real failure after large payload;
- resize while active, stale, and cleared.
