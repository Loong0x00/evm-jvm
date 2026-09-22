# MC-LOCALE-ROOT-P1 generated preflight

This is a bounded, generated-only append from `parent-949992642`. It appends
bootstrap image96 (`index 95`) `java/util/Locale`, retaining all 95 prior image
bytes/order, raw limits `69/449904`, native binding count 16, String-local
binding count 11, exception kinds 14, and the 393216-byte LOCAL engine cap.

`Locale` is an exact Java-8 (`javac -source 8 -target 8 -g:none`) 285-byte
image with only public final `ROOT`, private `Locale()V` chaining to Object,
and `<clinit>` allocating ROOT. It has no instance fields and no locale default,
language/country, factory, formatting, or case API. The source verifier checks
that image metadata and Code, reconstructs the exact direct-parent delta,
checks every first-95 leaf against the prior list, then independently derives
the 96-leaf root:

- Locale SHA-256: `8401495628aed9de6e7c7c0ad56f73ac563bd5e7a892b8eb8ca9fcf91bc03e31`
- Locale Keccak-256: `cb4ec03973fafc97a59f911f9c0b46f60b848ef0233807a96f1cdff84d904354`
- bootstrap root: `9d6ac1b79a64b66e5a4654eaf1b3afecafe61c3cff650b825152d278325c7e6c`
- engine: 378675 bytes, SHA-256 `f3d2b669b05e1ae04e7b5bfa961a25d2dad132a0c12fc78aedd3fefa141ed47d`, Keccak-256 `536e756899b808d5e91226ff347a310c2acc1afafb2311efad02fa68f3343328`
- coordinator: 5394 bytes, SHA-256 `7a4eda307afc57e2371e5e582ddaf7e00cdd7d6dfb6253ec4682e3d1f42fa896`, Keccak-256 `08b612b9a1b293bdad5e07243041c8a22c617230fac54039500a98caa29a5dc5`

## Reproduction

Run from the repository root with the pinned local Node dependencies and
JDK8 already present; the scripts reject network/shared dependency paths and
write all disposable build products below ignored `build/`.

```sh
python3 evidence/java-evm/minecraft-entry/locale-root-preflight/tools/build.py \
  build/java-diff-mc-locale-root-build-REPRO
python3 evidence/java-evm/minecraft-entry/locale-root-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-locale-root-fixtures-REPRO
python3 evidence/java-evm/minecraft-entry/locale-root-preflight/tools/gate.py \
  build/java-diff-mc-locale-root-build-REPRO \
  build/java-diff-mc-locale-root-fixtures-REPRO \
  build/java-diff-mc-locale-root-gate-REPRO
```

The committed `results.json` records the successful 36.541046s gate, fixture
and artifact SHA-256 values, all q1/q7/direct/reopen terminal roots, raw and
malformed input refusals, the omitted `Locale.getDefault()` member refusal,
and 634 independently re-encoded receipt chains. It also records the class
literal no-init inspection and `ROOT`'s single nonzero packed reference.
`SHA256SUMS` covers all durable stage files (except itself).

This is not an original-JAR replay, resource/class-loader/network run,
Minecraft/world/EULA/Done claim, or a general `Locale` implementation. No
original class, JAR, resource, network input, or other worktree was opened by
the stage.
