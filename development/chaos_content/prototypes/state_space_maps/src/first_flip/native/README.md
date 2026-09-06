# Native first-flip loop

`first_flip_loop.c` is the production copy of the validated investigation
event driver. It is built against the vendored SciPy DOP853 sources in
`src/lyapunov/s1_native/` and retains their `LICENSE_DOP` license.

The first-flip artifact builder applies four reviewed equivalence corrections
to its private build inputs: the dense-output `nfcn += 3` pointer correction,
strict terminal-horizon clamping, the `fac11 / safe` rejection factor, and
SciPy-equivalent controller bounds of 0.2 / 10. It never edits the S1 source.
The original and corrected source digests, correction set, and controller
settings are part of the artifact identity.
