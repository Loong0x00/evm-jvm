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
