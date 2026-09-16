# Result: bounded `Object.getClass()` source stage

**Status:** generated-only stage completed from accepted `parent-5f01fbbdf`; this is
not an original-JAR, loader/resource, Minecraft, world, or Done claim.

## Exact source delta and pins

- Bootstrap slot0 alone is replaced. The Java 8 Object image SHA-256 is
  `9e86081e4b58c8cc62f9ae0fa0e8a724e853c5b4875a3f9cd2bf03e26594c1e7`;
  the other 85 of 86 bootstrap images are source-verified byte-identical to the
  accepted parent.
- Binding13 is only `Object.getClass:()Ljava/lang/Class;`, requires
  `public final native` (`0x0111`), rejects a raw Object replacement, and
  routes the ordinary non-null receiver dynamic class through the canonical
  guest Class-mirror allocator. It does not initialize the target.
- Built engine: 388546 bytes (cap 393216), runtime SHA-256
  `1247c735b4f2d5625761a3acd6eba7440c2eb392e1e32f8feb51142d01d2dc99`,
  Keccak `d985017157caf2427f11b41128b0f90a389cbd5263c080bb3e2c9eb94165bc61`.
  Coordinator: 4145 bytes, runtime SHA-256
  `5d074bf18845e3454f6c4389e99f18db9535e26fc342b4f81dca8db70b4c9b24`.
- Retained pins: raw `32/262144`, diagnostic bound 118, frames 128,
  checkpoint 1048576, head 32768, kinds 14, String-local binding10,
  reserve 25000000, and external LOCAL gas 1000000000.

## Reproducible run

One source build created
`build/java-diff-mc-object-get-class-build-405f153bd`; its final source verifier
validated all six parent inputs and the built pins. Fixtures were generated in
`build/java-diff-mc-object-get-class-fixtures-f4d237052`. The full generated
receipt gate completed in 207.124 seconds at
`build/java-diff-mc-object-get-class-gate-13b6816ac`:

- 54 result rows, 293 commands, and 2807 independently canonicalized public
  receipts passed.
- Dynamic identity has matching q1/q7/direct terminal state: 50 Java and 3
  internal steps, machine root
  `0x94a971809b9559653d89f43aa123e668addb97e535293049fadf104c275bf1ba`,
  opaque SHA-256
  `cf18a735393df8e2f958007c1b39faf108eea67ba177a2ea5d2b92c51cbd82f2`.
- No-init has matching q1/q7/direct state (9 Java/2 internal), and leaves its
  Dormant target uninitialized. Null follows the catchable NPE path with
  matching q1/q7/direct state (8 Java/3 internal). Raw Object remains ordinary
  authored Code under the same three quanta (13 Java/2 internal).
- Array, primitive-literal, and forged-Class paths refuse without a Head. The
  allocator OOM witness finishes catchably after 13316 Java/3 internal steps;
  it is direct/reopened only, because a q1 run would persist 1023 allocation
  checkpoints. The retained generic OOM gate still runs q1/q7/direct.

The disposable gate summary SHA-256 is
`c0bf615475b0db779217236300c21b3f51fc0836acb25a4fbe7d7c8052fb9002`.
Tracked stage source hashes are: engine
`4afae51b3392d13d4664fa8ee82901b42eff4672d5a23acb38c1a0da2b4fdcb1`,
coordinator `8b16ffbe6d27ba710754336e9291f2a67b5fa90c526cd4e195bf1d5e0aa77b50`,
driver `5272da45ff17e95c85877e2de36e3a5e16a37d166d183ed6e425ea4fc73a99b2`,
and pins `bfe529ce8108c79fbdf6ab184167384ead9b2408815f79df406ee3aed988e4e9`.

Reproduce with the three commands in [README.md](README.md). The gate uses only
generated Java 8 fixtures and does not access an original artifact.
