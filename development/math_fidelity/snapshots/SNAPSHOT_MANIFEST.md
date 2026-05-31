# Source Snapshot Manifest

Date: 2026-05-31

This snapshot is diagnostic evidence for Phase 8 mathematical fidelity work. It
is not production code and must not become an app runtime dependency.

## Snapshot Location

`development/math_fidelity/snapshots/simple_model_source/`

The probe scripts add this directory to `sys.path` and import the copied package
as `double_pendulum_snapshot`.

## Files Copied

| Snapshot file | Production source |
| --- | --- |
| `simple_model_source/double_pendulum_snapshot/__init__.py` | `src/double_pendulum/__init__.py` |
| `simple_model_source/double_pendulum_snapshot/math/__init__.py` | `src/double_pendulum/math/__init__.py` |
| `simple_model_source/double_pendulum_snapshot/math/functions.py` | `src/double_pendulum/math/functions.py` |
| `simple_model_source/double_pendulum_snapshot/models/__init__.py` | `src/double_pendulum/models/__init__.py` |
| `simple_model_source/double_pendulum_snapshot/models/hamiltonian.py` | `src/double_pendulum/models/hamiltonian.py` |
| `simple_model_source/double_pendulum_snapshot/models/initial_conditions.py` | `src/double_pendulum/models/initial_conditions.py` |
| `simple_model_source/double_pendulum_snapshot/models/lagrangian.py` | `src/double_pendulum/models/lagrangian.py` |
| `simple_model_source/double_pendulum_snapshot/models/metadata.py` | `src/double_pendulum/models/metadata.py` |

## Modification Status

The copied file contents were not modified after copying.

The only structural change is the containing package path:

- production package: `src.double_pendulum`
- diagnostic snapshot package: `double_pendulum_snapshot`

The copied files use relative imports, so no source import rewrites were needed.

## Scope

This is the minimum production source needed by the simple-model drift probe to
instantiate the current simple Lagrangian and Hamiltonian model classes, build
their symbolic equations, convert Hamiltonian initial angular velocities to
canonical momenta, and collect solver metadata.

The snapshot intentionally does not include Dash app code, Canvas rendering,
callbacks, UI components, validation wrappers, plotting helpers outside the
model modules, documentation, tests, or compound-model investigation material.
