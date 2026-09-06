# First-flip logarithmic-class convergence

This bounded follow-up asks whether the model-independent observable name
“first-flip logarithmic class” remains reproducible for the equal-link simple
double pendulum after exact chaotic trajectories cease to agree.

Artifacts:

- [decision report](FIRST_FLIP_LOG_CLASS_CONVERGENCE.md);
- [deterministic case definition](selected_cases.json);
- [machine-readable evidence](evidence/first_flip_log_class_convergence.json);
- [single diagnostic matrix](evidence/first_flip_log_class_convergence.png).

Run the 26-case, three-policy experiment from the repository root:

```bash
MPLCONFIGDIR=/tmp/dp-mpl XDG_CACHE_HOME=/tmp/dp-xdg NUMBA_CACHE_DIR=/tmp/dp-numba \
  uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.first_flip_log_class_convergence.first_flip_log_class_convergence
```

The command performs 78 independent `solve_ivp` evaluations, each terminating
at the first event or at $\widehat H=10000$. It uses at most four spawn workers.
It neither calls nor changes the production-native route; all three long-horizon
policies are asserted to remain outside the exact-$T=5$ production allowlist.

The case list is checksummed to the previous 128×128 exploratory evidence. The
new evidence in turn records the case-definition and diagnostic checksums, the
full physical/numerical contract, every policy result, every gate outcome, and
the derived convergence analysis.
