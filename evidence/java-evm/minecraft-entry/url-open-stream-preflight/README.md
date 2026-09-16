# Generated bounded `URL.openStream()` source stage

This stage derives from accepted `parent-f7e2ad683` only. It replaces bootstrap
slot 62 (`java/net/URL`) with a Java 8 ordinary `openStream()` body that creates
`File("/ro/" + resourceName)` and `FileInputStream`; URL constructor, equality,
hash and string Code remain ordinary Java. The engine delta is otherwise only a
fresh commitment domain.

The fixed coordinator and raw-byte driver accept zero or one selected resource.
A selected name is explicit generated-fixture metadata (ASCII, 1..256 bytes),
its DI0 decoder/index/final-root/size are validated in EVM, and its exact DI0
bytes are seeded read-only at `/ro/<name>` on `startMain`. The coordinator has a
scalar seed slot, max 4096 bytes; `resumeMain` never reloads it and uses the
checkpointed VFS. There is no host ZIP parser, inflater, content injection or
catalogue: the driver provides only opaque generated ZIP bytes to AS0, then
EVM AS0/ZI0/DI0 performs all lookup and decode/read operations.

`tools/verify_source.py` pins the accepted parent sources, compiles the URL
source with local Java 8, proves its byte-identical embedded image, and proves
that the engine changes only domain constants and slot 62. It also checks raw
32/262144, 86 bootstraps, native 13, diagnostic 118, frames 128, checkpoint
1 MiB, and the 393216-byte engine cap. The full generated gate retains the
Object.getClass/raw32/lock/TreeMap/String/EnumSet/queue/OOM/canonical-receipt
corpus and adds generated ZIP resource enumeration, URL reads/EOF/close,
read-only preservation, absent resource, resource scalar/count, 4096/4097,
and root/address-tamper checks.

Reproduce using only pinned local toolchains:

```sh
python3 evidence/java-evm/minecraft-entry/url-open-stream-preflight/tools/build.py build/java-diff-mc-url-open-stream-build-LOCAL
python3 evidence/java-evm/minecraft-entry/url-open-stream-preflight/tools/generate_fixtures.py build/java-diff-mc-url-open-stream-fixtures-LOCAL
python3 evidence/java-evm/minecraft-entry/url-open-stream-preflight/tools/gate.py build/java-diff-mc-url-open-stream-build-LOCAL build/java-diff-mc-url-open-stream-fixtures-LOCAL build/java-diff-mc-url-open-stream-gate-LOCAL
```

Only generated Java 8 classes and generated ZIP resources are used. No original
artifact, JAR, class, resource, provider, factory, world, Minecraft run or Done
claim is made here.
