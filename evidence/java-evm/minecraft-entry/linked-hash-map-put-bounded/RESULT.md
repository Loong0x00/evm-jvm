# P59 worker candidate result

Status: **implementation and focused candidate gates completed; not accepted**. Parent-independent rebuild, complete retained-profile compatibility gates, and later original143 gate remain pending. No push or production integration was performed.

## Implementation

- Guest Java change is limited to image 113 `java/util/LinkedHashMap`; appended exactly three ordinary helpers at indices 124–126: linked entry, live entry-set view, and independent iterator. P58 EnumMap image 123 stays staged raw and byte-identical. Other accepted images are intended unchanged; parent must independently verify the full 0–122 prefix.
- The new backend uses genuine guest linked entries, inherited size/modCount/entrySet cache, stable insertion order, incoming-key equals direction, same-node value replacement, fresh content `hashCode`, typed-array fit behavior, and explicit refusal for unsupported inherited APIs. The inherited HashMap table remains unused; this candidate makes no bucket/resize/treeification claim.
- No global quota, storage/ABI/checkpoint schema, accepted image, HashMap `Node`, EVM accounting rule, or core geth code was changed.
- Engine runtime: 454,849 bytes, SHA-256 `c9fa203c18b641a07d7319c8574ad75f8acbf0c24c0a53423bf77273f2caeb57`, Keccak `b1d041cb3ac93176793771fbb43927688a59499932a2aa16ffa1ad176896bcf1`.
- Coordinator runtime: 5,411 bytes, SHA-256 `19e3a48ed41fdbf54cfa487d4c000a618eb2421c6a4168a30e305548b615d38d`, Keccak `c66195ae0abfe7621709724bcb594d3b841672da0e01e88844bc1dc90b74baec`.
- Bootstrap count 127; raw class bound 150, diagnostic total 277, max class index 276. Bootstrap root `f6db289dfefffb5885b7a61c8977112f5cef5c71c00ea86868b4b62fc9f74d13`. Rebuilt P58 root leaves match byte-for-byte at every index except changed 113; old EnumMap index 123 is unchanged. Eight P58 bootstrap compile-context sources were byte-identical; the only changed source is LinkedHashMap plus the three approved helpers.
- `build-java.sh` emits all four changed/new class images with classfile major version 52 and `-g:none` (no line/local-variable debug tables).

## Focused generated evidence

| Case | Result |
|---|---|
| `world-basic-typed-final` | Genuine terminal lifecycle/outcome 2; 9,274 JVM steps, 20,147-byte checkpoint, gas 4,404,563,896; covers empty LinkedHashMap key and opaque value, callback count/direction, fresh content hash, replacement/alias/order, entrySet/iterator, null behavior, setValue, CME/NSEE order, typed-array same target/trailing slots/NPE/ASE, Map/HashMap/LHM dispatch. Fixture SHA-256 `6f7a9cc7cd88b418f983dbc3256a7e3f8e5875b225e05e18f2b2526f87c10056`. `verify` succeeded in a separate process.
| `world-callback-q1` vs `world-callback-q7` | Both terminal with outcome 2, 369 JVM steps, 11 internal steps, identical machine root `0x88f4c58155f6815b87a00b2557559600063b0afb66b3319a202f18ecbcfcd23c` and VFS root `0xb9ade9c249842d1217e08894ba6593b8d2b5580f036ccdda4a462ee62d03480b`; 369 q1 slices vs 53 q7 slices. The fixture checks hash/equals callback-thrown ArithmeticException and no outer insertion/replacement. Both worlds reopened and verified.
| `world-collision-eight` | Eight distinct keys with identical spread hash insert and enumerate in insertion order; terminal outcome 2, 2,576 JVM steps, 575,465,494 gas.
| `world-collision-reproducible` | Prospective ninth same-hash key raw-refuses with `CallError(4,164)`; durable Head unchanged.
| `world-reentrant-reproducible` | Structural insertion from key hash callback raw-refuses with `CallError(4,31)`; durable Head unchanged.
| `world-equals-reentrant` | Structural insertion from incoming-key equals callback raw-refuses with `CallError(4,122)`; durable Head unchanged.
| `world-short-array-refusal` | Short typed target raw-refuses with `CallError(4,14)`; durable Head unchanged.
| `world-map-equals-final`, `world-view-equals-final`, `world-inherited-get-refusal` | Unsupported full map equality, view equality, and inherited `get` each raw-refuse with `CallError(4,18)`, `(4,30)`, `(4,20)` respectively; durable Head unchanged.

Fixtures are trusted, locally generated Java 8-target class files. `build-fixtures.sh` runs host smoke assertions and writes deterministic stored ZIPs. The host JVM is only a test oracle; no host execution path was added to the guest runtime.

## Reproduction and remaining gates

From this directory: `bash build-java.sh`; set `NODE_PATH` to the existing local pinned solc dependencies and run `node engine/build.js` then `node coordinator/build.js`; run `bash build-fixtures.sh`. The focused EVM commands and full per-world receipts are under `tests/reports/`; checkpoints/world state are retained under `tests/world-*`. See `pins.json`, `BUDGET_NOTE.md`, and `candidate-manifest.json` for code, root, fixture, and file hashes.

The candidate test-driver gas allowance is now 8B only after measured 1B, 2B, and 4B test-budget failures. The 1B/2B/4B worlds and receipts remain preserved. The final 8B allowance does not change accepted quotas or EVM rules.

Not run/claimed: parent-independent full accepted-profile prefix and legacy controls, raw150 boundary suite, complete candidate test matrix across all quanta, standard CREATE/EIP170, original143, Minecraft execution, production acceptance, or push. A diagnostic Map-equality world was initially created at an adjacent path due a command typo, then moved intact into this candidate. An `rmdir` command was attempted on only the now-empty directories created by that typo; no world/receipt data was removed.
