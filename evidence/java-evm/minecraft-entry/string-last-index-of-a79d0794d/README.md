# Bounded `String.lastIndexOf(String)` generated evidence

Source commit `a79d0794d` replaces only slot 26 (`java/lang/String`) from accepted
`parent-31e5a573c`. The Java-8 image is 1187 bytes,
`2fbfe5d57906f5ebd4f2eeaceb209edf8d4a619afb21d1531f7aaea121506033`.
It preserves the predecessor source verbatim except for ordinary guest-Code
`lastIndexOf(String):int`, implemented through accepted `length()` and
`charAt(int)` primitives. Its first action is `target.length()`, so a null
target takes the existing guest NPE path.

The pinned optimizer200/viaIR source build produced a 386525-byte engine under
the 393216-byte cap (6691-byte headroom), with the exact runtime hashes in
`pins.json`. The generated-only gate passed in 184.06887695100158 seconds:
2565 canonical receipts across 67 successful worlds and 213 commands. It covers
q1/q7/direct/reopen suffix, middle, prefix, overlap, repeated, absent, empty,
longer-target, BMP UTF-16 and surrogate-pair cases; a catchable null-target NPE;
and an uninitialized-String diagnostic. It also retains StringBuilder,
System.err, failed-init, raw30/31, byte-boundary, EnumSet/ACC_ENUM, queue and
OOM controls.

Reproduce only from local pinned inputs (no network or original server artifact):

```sh
python3 evidence/java-evm/minecraft-entry/string-last-index-of-preflight/tools/build.py \
  build/java-diff-mc-string-last-index-of-build-a79d0794d
python3 evidence/java-evm/minecraft-entry/string-last-index-of-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-string-last-index-of-fixtures-a79d0794d
python3 evidence/java-evm/minecraft-entry/string-last-index-of-preflight/tools/gate.py \
  build/java-diff-mc-string-last-index-of-build-a79d0794d \
  build/java-diff-mc-string-last-index-of-fixtures-a79d0794d \
  build/java-diff-mc-string-last-index-of-gate-a79d0794d
```

This is generated-only bounded String evidence. It does not run or inspect an
original Minecraft artifact, and makes no substring, broader String, Minecraft,
or Done claim.
