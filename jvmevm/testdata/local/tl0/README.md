# LOCAL MC-TL0 trusted fixtures

This directory pins the frozen 24-root MC-TL0 Throwable corpus. The five source
files are hygienic Java sources compiled with `javac --release 8 -g:none`.
`manifest.json` records every source hash, selected raw bundle and class hash,
entry, arguments, and exact returned or uncaught outcome. Every selected bundle
contains at most three classes and is far below 64 KiB.

The roots exercise real allocation, constructor chains and writes, object/field/
array identity, handler and call unwind, rethrow, class initialization wrapping,
erroneous second use, exact-known versus dynamic subclass outcomes, and legal
post-super constructor-receiver escape. In particular the four constructor-self
roots return 101, 102, 103 and 201 through genuine effects; they are not constant
outputs. The host-only test oracle separately checks that the initialization
wrapper cause is the exact escaped receiver.

Regenerate with `./build_fixtures.py`. The Go harness also requires both Java 8
and Java 21 oracles and byte-compares a clean Java 8 rebuild to these pinned
classes. Java is used only to build trusted test inputs and as a test oracle;
production Go transports the classfiles, checkpoint and `javaClass` ABI bytes
opaquely. This is not Java SE conformance, VFS, Minecraft execution, EULA
acceptance, RPC, P2P, or a listener.
