# MC-VFS0a trusted fixtures

This directory pins the frozen VFS0a Java-8 corpus: exactly 24 static integer
roots in the `Paths`, `Streams`, and `Errors` groups listed in
`JAVA_EVM_MC_VFS0A_PLAN.md`. `build_fixtures.py` compiles the three self-authored
sources with `javac --release 8 -g:none`, copies only the three named raw
classfiles, and records source/class SHA-256 values.

Manifest seeds are ordered opaque `pathHex`/`dataHex` bytes plus `readOnly`; the
production Go transport does not parse or materialize them. Tests alone decode
these trusted records to create an owned host-oracle directory. Java 8 is the
primary C-locale oracle and Java 21 is secondary. All 24 currently return 1 on
both JDKs; there are no Java-21 differences to retarget. The message roots pin
slash-normalized prefixes and the Linux C/POSIX suffixes in the frozen plan.

The stream roots cover independent descriptors, truncation before constructor
binding, append at current EOF, zero-filled gaps, stale cursors beyond EOF,
closed descriptors, and Java null/bounds/zero-length precedence. They do not
provide host files to production execution: EVM `start` receives only the raw
seed records and all path, inode, descriptor, byte, message, and Java effects
are runtime-owned.

`regressions/` is a separate post-freeze seven-root bundle for the path blocker in
`JAVA_EVM_MC_VFS0A_PATH_REVIEW.md`. It pins Java 8/21 C-locale ENOENT/ENOTDIR
results for input and output opens through missing/file prefixes and the measured
`mkdir == false` but `mkdirs == true` distinction. It does not alter the original
24-root manifest, sources, classes, IDs, or expectations. Its actual-EVM test is a
mandatory correction gate, not evidence that the currently integrated old runtime
passes.
