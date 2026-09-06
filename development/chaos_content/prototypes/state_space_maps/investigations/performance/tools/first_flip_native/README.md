# Native first-flip prototype source

`first_flip_loop.c` is investigation-only event machinery around the production
S1 vendored DOP853 source at `src/lyapunov/s1_native/dop.c` and `dop.h`.

The vendored solver is distributed under the license retained at
`src/lyapunov/s1_native/LICENSE_DOP`. The prototype build consumes that source
directly; it does not duplicate or modify the licensed production files.

Dense-output mode exposes a dormant `nfcn += 3` pointer-increment defect in the
vendored C translation. The Python build tool asserts that exact source line and
writes a temporary corrected build copy containing `*nfcn += 3`. The production
source and its validated S1 digests remain unchanged.
