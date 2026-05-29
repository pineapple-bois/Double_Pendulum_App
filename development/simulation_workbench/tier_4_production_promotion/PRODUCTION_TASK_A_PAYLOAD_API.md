# Production Task A: Canvas Payload API

Tier: Phase 6 / Simulation Workbench Tier 4
Task type: production implementation plan

## Goal

Implement the Python-side Canvas payload API and tests before wiring Canvas into
the live `/simulation` page.

Task A must not change the production Simulation UI and must not add the Canvas
renderer to the page.

## Proposed Helper API

Recommended helper functions:

```python
def build_canvas_motion_payload(..., run_id: int) -> dict:
    """Build a JSON-serializable Canvas payload for a simulation result."""


def validate_canvas_motion_payload(payload: dict) -> list[str]:
    """Return schema, units, shape, finite-value, and status problems."""


def estimate_canvas_payload_size(payload: dict) -> int:
    """Return compact JSON size in bytes."""


def summarise_canvas_payload(payload: dict) -> dict:
    """Return compact diagnostics without large arrays."""
```

Recommended location after implementation inspection:

- app-layer serialization code under something like `app/serialization/`; or
- a small app-facing helper module if the repository already has a better
  pattern.

Keep reusable numerical/model helpers under `src/double_pendulum/` only when
they are independent of Dash and UI payload concerns.

## Required Payload Content

The production payload should include:

- schema version;
- run ID or animation epoch;
- status;
- model type;
- system type;
- request label or preset name if available;
- time samples with units;
- angular displacement samples with explicit units;
- angular velocity samples only where meaningful and audited;
- bob position samples with explicit units;
- sample count;
- duration;
- user-facing initial conditions;
- internal initial state summary;
- state units;
- position units;
- solver metadata;
- warnings;
- bounds or scale hints;
- payload size bytes.

## Status Rules

`success`:

- may contain drawable arrays;
- must include solver metadata and warnings.

`stale`:

- may contain drawable arrays;
- must be distinguishable from `success`;
- must not autoplay as current.

`failed`, `cleared`, `empty`:

- must not contain drawable success arrays;
- may contain messages and compact diagnostics.

## Python Tests Required

Add tests for:

- schema shape;
- consistent array lengths;
- finite arrays;
- explicit units;
- payload size estimate;
- solver metadata included;
- simple Lagrangian payload;
- simple Hamiltonian payload with nonzero angular velocities;
- compound Lagrangian payload;
- compound Hamiltonian payload with nonzero angular velocities;
- failed payload does not contain drawable success arrays;
- cleared payload does not contain drawable success arrays;
- stale payload is distinguishable from success;
- no energy diagnostics are implied;
- Hamiltonian momentum is not mislabeled as angular velocity.

Suggested new test file:

- `tests/unit/test_canvas_payload.py`; or
- `tests/numerical/test_canvas_payload.py` if model construction is required.

## Representative Cases

Cover at least:

- simple Lagrangian baseline;
- simple Hamiltonian nonzero velocity;
- compound Lagrangian larger-angle or baseline case;
- compound Hamiltonian nonzero velocity;
- one longer-duration or higher-sample payload summary check.

## Acceptance Criteria

Task A is accepted only when:

- payload helper exists in production code;
- tests cover payload schema and representative model/system combinations;
- units are explicit;
- Hamiltonian momentum is not serialized as angular velocity;
- status-specific drawable/non-drawable rules are tested;
- payload size can be estimated;
- no production UI is changed yet;
- no Canvas renderer is wired into `/simulation` yet;
- payload API is ready for the renderer integration task.

## Explicit Non-Goals

Do not include:

- production Canvas renderer;
- `/simulation` layout changes;
- callback rewiring;
- CSS changes;
- energy diagnostics;
- chaos diagnostics;
- comparison runs.
