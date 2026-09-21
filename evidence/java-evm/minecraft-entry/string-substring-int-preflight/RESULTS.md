# Generated-only String.substring(int) preflight result

This is a bounded generated-fixture result, **not an accepted profile or an
original-JAR/Minecraft replay**.  It records the reproducible run required by
`JAVA_EVM_MC_STRING_SUBSTRING_INT_PREPARATION.md`.

## Scope proved

- Only bootstrap slot 26 (`java/lang/String`) changed.  It is the Java-8
  `String` image with the exact native declaration
  `substring(I)Ljava/lang/String;`.
- Valid `begin` in `0..length` preserves UTF-16 code units.  Begin zero returns
  the receiver; every nonzero suffix (including a length-zero suffix) is a
  fresh String with a fresh copied `char[]`.
- Invalid negative/past-end begins refuse with the established
  `StringProfileError(1, pc)` selector `0x32e310eb`; `substring(int,int)`
  remains absent and refuses atomically.  The allocation-bound fixture catches
  the existing guest OOME after 1022 complete owned suffixes, with its final
  complete suffix still usable.
- No valid substring case initializes `String`; no global native binding,
  bootstrap count, raw cap, frame cap, checkpoint cap, or root ordering was
  widened.

## Commitments and build

- Domain: `MC-SUBSTRING-INT-00001`
- Bootstrap count: 94; changed slot: 26 only
- String image: 1547 bytes; SHA-256
  `04f9fa3748fae92840942cfa6dbf2cfb0f3845f0320273c33ada18d81a3bd231`; Keccak-256
  `fa2609af1a1b40f8ede90e7d8f34dfb2bd1586edfa247a02f33e48c5439487be`
- Ordered bootstrap root:
  `7f7e1d7f3e44ffe70415e4075f7a94e02c2b1835e6c63b983f0d152d64d312c4`
- Rebuilt engine: 373596 bytes (cap 393216), runtime SHA-256
  `2a280fd0b55658436a5527d0d3b1b0e50002d77cc97048eb5cc8b71d41528f12`,
  Keccak-256 `075c34299204cf7428989a07dd8e9cd90c1aa6d2f4915147f52e7aa630baac21`.
- Rebuilt coordinator: 5394 bytes, runtime SHA-256
  `b007e1afaaa6287504b22f8c019a90ab208a125f62f3dbe36689793d3e6e243a`,
  Keccak-256 `3fbe5b16469a891e42bdfa8766ed6073da055cfb81f59e6243380cf751d84ba6`.

## Reproduction

The following fresh outputs were produced under ignored `build/` directories:

```sh
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/build.py \
  build/java-diff-mc-string-substring-int-build-full1
python3 evidence/java-evm/minecraft-entry/index-out-of-bounds-string-constructor-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-index-out-of-bounds-string-constructor-fixtures-substring-full1
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/generate_fixtures.py \
  build/java-diff-mc-string-substring-int-fixtures-full1
python3 evidence/java-evm/minecraft-entry/string-substring-int-preflight/tools/full_gate.py \
  build/java-diff-mc-string-substring-int-build-full1 \
  build/java-diff-mc-index-out-of-bounds-string-constructor-fixtures-substring-full1 \
  build/java-diff-mc-string-substring-int-fixtures-full1 \
  build/java-diff-mc-string-substring-int-full-gate-full1
```

The final command passed in 862.209204384 seconds (limit: 1200), issued 567
commands, and independently canonicalized 13314 public receipts.

## Durable metadata archive

`results/` retains only metadata from that already-completed run:

- `build-summary.json` and `source-verification-summary.json` record the
  successful rebuilt artifacts and source/root verification.
- `full-gate-summary.json` is the complete generated-only gate summary.
- `canonical-receipts.json` is the independent canonical receipt aggregate;
  `timing.json` records all 567 command outcomes/timings and the whole-gate
  timing.
- `manifest.json` binds every archived copy to its ignored completed-run source
  and records the canonical verifier invocation result. `SHA256SUMS` hashes all
  archived files; verify it with `cd results && sha256sum -c SHA256SUMS`.

The archive contains no JAR/ZIP input, compiled class, world, LevelDB data,
checkpoint, executable, or other binary. The full-gate summary SHA-256 is
`f1be5954b520ae2285e907ed88eb4b4080ac1c23cec5f1c5db42f0a6c73e2eb5`.

Focused valid cases were identical across q1/q7/direct/reopen:

| fixture | Java steps | q1 epochs | q7 epochs |
|---|---:|---:|---:|
| UTF-16 suffix | 42 | 42 | 6 |
| ASCII + fresh empty suffix | 47 | 47 | 7 |
| begin-zero identity / nonzero freshness | 37 | 37 | 6 |
| empty receiver | 16 | 16 | 3 |

The retained generated corpus was rerun direct/reopen; its historical q1
corpus remains deliberately omitted so the whole gate stays within the fixed
1200-second bound.  Inputs are generated Java-8 source only: no original
artifact/JAR, resource, provider construction, factory execution, world, EULA,
or Done input/claim occurred.
