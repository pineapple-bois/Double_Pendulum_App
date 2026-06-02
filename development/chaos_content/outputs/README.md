# Chaos Sandbox Outputs

This directory is reserved for generated Phase 10 chaos-content diagnostics.

Output bundles are reproducible sandbox artifacts, not production assets. They
may contain JSON summaries, CSV section points, and diagnostic PNG plots written
by commands such as:

```bash
python development/chaos_content/experiments/hamiltonian_poincare/minimal_hamiltonian_poincare.py --output-dir development/chaos_content/outputs/smoke_run --plots
```

Generated run artifacts under this directory are ignored by git. Keep only this
README and `.gitignore` tracked unless a future task explicitly asks for a tiny,
documented output artifact.
