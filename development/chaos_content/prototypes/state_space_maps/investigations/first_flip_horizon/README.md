# First-flip horizon and energy accessibility

This bounded investigation selects an observation horizon for the roadmap's
logarithmic first-flip pedagogy and derives the rigorous zero-velocity
energy-inaccessibility mask for the actual equal-link simple model.

The accepted evidence is the 128×128 periodic study through
$\widehat T=100$:

- [decision report](FIRST_FLIP_HORIZON_AND_ENERGY_ACCESSIBILITY.md);
- [summary evidence](evidence/first_flip_horizon_128.json);
- [deterministic arrays](evidence/first_flip_horizon_128.npz);
- [decision diagnostic](evidence/first_flip_horizon_128.png).

Run it from the repository root:

```bash
MPLCONFIGDIR=/tmp/dp-mpl XDG_CACHE_HOME=/tmp/dp-xdg NUMBA_CACHE_DIR=/tmp/dp-numba \
  uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.first_flip_horizon.first_flip_horizon_and_energy_accessibility
```

The tool refuses resolutions above 256 and does not use or change the
production field runner's T=5 eligibility. It calls the immutable corrected-v2
native artifact through an investigation-local boundary, retains the existing
solver/event/diagnostic gates, uses four spawn workers, and recycles pools every
2,048 cells.

## Rejected extra decade

The optional $\widehat T=1000$ probe is retained only as rejected exploratory
evidence:

- [exploratory summary](evidence/first_flip_horizon_128_through_H1000_exploratory.json);
- [exploratory arrays](evidence/first_flip_horizon_128_through_H1000_exploratory.npz);
- [exploratory diagnostic](evidence/first_flip_horizon_128_through_H1000_exploratory.png);
- [tail validation](evidence/first_flip_H1000_tail_validation.json).

Recheck its decisive late/worst-drift cases against the trusted Python
`solve_ivp` implementation with:

```bash
MPLCONFIGDIR=/tmp/dp-mpl XDG_CACHE_HOME=/tmp/dp-xdg NUMBA_CACHE_DIR=/tmp/dp-numba \
  uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.first_flip_horizon.validate_exploratory_tail
```

The late $\widehat T=1000$ case fails the existing event-time, event-state, and
attribution equivalence gates. Its aggregate population is not accepted as an
authoritative field result.

