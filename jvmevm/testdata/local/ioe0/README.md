# MC-IOE0 trusted fixtures

This directory pins the frozen IOE0 Java 8 fixture corpus. `build_fixtures.py`
compiles the three self-authored sources with `javac --release 8 -g:none`, copies
only the classfiles named by the manifest, and records source/class SHA-256s.

The manifest has exactly 24 static integer roots: eight each in `IOE0Messages`,
`IOE0Origins`, and `IOE0Causes`. All return 1 except `failedClassLater`, which
returns 3. The values require constructor field writes, exact String/Throwable
reference identity, ordinary and VM-origin causes, virtual dispatch, catch/rethrow,
and failed-class state; they are not constant-only probes. Bundles contain at most
four unchanged raw classes and 64 KiB.

Java 8 is the primary host-only oracle and Java 21 is a secondary comparison.
Neither host JVM participates in EVM execution. The paired positive roots avoid
VM-origin ArithmeticException `getMessage`, which is deliberately a hard profile
error in IOE0 rather than a fabricated Java value. Synthetic Object-publication
codec probes are EVM-only and are not substitutions for host-JDK oracle rows.
