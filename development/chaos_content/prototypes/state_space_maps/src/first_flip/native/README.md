# Native first-flip loop

`first_flip_loop.c` is the production copy of the validated investigation
event driver. It is built against the vendored SciPy DOP853 sources in
`src/lyapunov/s1_native/` and retains their `LICENSE_DOP` license.

Dense output needs the reviewed `nfcn += 3` to `*nfcn += 3` correction. The
first-flip artifact builder applies that single correction to a private staged
copy of `dop.c`; it never edits the S1 source. Both original and corrected
digests are part of the artifact identity.
