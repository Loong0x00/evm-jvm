# ClassLoader type-only generated preflight evidence

`gate.py` is a source-only reproducer based exclusively on
`parent-a30955bb0` evidence. It never opens original Minecraft payloads,
classes, pages, worlds or LevelDB. It builds only the minimal abstract Java8
`java.lang.ClassLoader` image with protected `()V` Object construction, checks
all nine engine domain strings are renewed, and verifies the existing 49 image
bytes before appending index49.

The Java8 fixtures test subclass/protected construction, `ClassLoader[]`, cast,
null and literal identity. They also preserve an honest caller replacement
refusal and an unsupported `getSystemClassLoader` member refusal. The gate uses
one inherited process group, absolute fresh ignored build output, LOCAL1B and
the unchanged finite timing/RSS/cap limits. `artifacts/` is created only by a
successful gate and excludes Go binaries, LevelDB, original payloads and worlds.

Fresh result: 195.178s/52572KiB; 136B ClassLoader SHA-256
`df3b18c48b514343c2dcf9d025afd714027e319db03174c8f831215645f39e8b`; engine
323026B Keccak`35f8925e4f8631a9ff23cb5faec1ed6c4db2c0e3d318c9fa21c70693e69a0258`.
q1/q7/direct/reopen agree at53 Java/3 internal and genuine VOID. The two honest
refusals are caller replacement`0x6a23ad80` and getSystemClassLoader
CallError`0xd631c3a4`, both root-unchanged. See `artifacts/results.json` and
`SHA256SUMS` for the full receipts and pins.
