# Properties construction/storage COPY preflight

**PARENT CORRECTION:** recovered after WebSocket stop; independent subclass
probe found virtual-get interception in getProperty. Parent fixed only that to
super.get, retained virtual put/defaults, and independently verified new pins.
Original20 now hits the unchanged reserve even at q1. See
JAVA_EVM_MC_PROPERTIES_PARENT_PREFLIGHT.md; worker claims below remain historical.

**Status: worker implementation evidence only; not parent-reviewed or accepted.**
This is an isolated continuation of
`evidence/java-evm/minecraft-entry/parent-6748eb593/`, based only on that
parent's `engine`, `coordinator`, `pins.json`, and
`executed_bounded_driver.go.txt`. No original JAR, class, resource page, world,
or prior arraycopy-worker driver was read or used.

## Scope and identity

* New profile/domain: `MC-PROPERTIES-PREFLIGHT1`.
* New LOCAL initial-state-only engine address:
  `0x4d4350524f504552544945535046000000000001`.
* Raw input remains **24 classes / 262144 bytes**. The coordinator's ordinary
  CREATE arrays remain 24. Existing `100M` ordinary gas, `25M` reserve, frame,
  checkpoint, Head, CP/Code, heap/VFS, and 320 KiB runtime caps are unchanged.
* The 45 inherited bootstrap bytes/order are retained verbatim. Three images
  append only after them: `java/util/Dictionary` (448 B), `Hashtable` (1823 B),
  and `Properties` (917 B). The bootstrap commitment has 48 image hashes.
* Exact source/artifact/bootstrap/fixture pins are in
  `evidence/java-evm/minecraft-entry/properties-preflight/pins.json`.
  Rebuild is pinned to solc `0.8.30+commit.73712a01.Emscripten.clang`, optimizer
  200, viaIR, Cancun, metadata off, and Java 8 javac.

## Minimal guest-Java surface

`Properties` genuinely extends `Hashtable<Object,Object>`; `Hashtable` extends
`Dictionary<K,V>` and implements the already-pinned `Map<K,V>`, `Cloneable`, and
`Serializable`. The owned source is archived under `bootstrap/java/util/` and is
compiled into the three committed class images. It provides only:

* no-argument and defaults `Properties` construction;
* linear, growable guest-object key/value storage using guest `Object[]` and
  existing native `System.arraycopy` only for backing-array growth;
* `get`, `put`, `remove`, `size`, `containsKey`, `clear`, `isEmpty`;
* `setProperty`, `getProperty(key)`, and `getProperty(key,fallback)` with real
  String-type/default-chain behavior.

Null key/value checks throw guest `NullPointerException`; overwrite/remove return
prior values. Non-String map values do not become String properties. Equality is
reference-or-existing virtual `equals`, so String aliases use the existing guest
String equality path. This intentionally does **not** claim `load`, `store`, XML,
enumeration, property-file parsing, System properties/environment, resource
search, concurrency, or a complete Hashtable/Properties API.

The interpreter rejects caller-supplied `java/util/Dictionary`, `Hashtable`, or
`Properties` as reserved platform overrides with the existing
`BootstrapProfileError(1,inputIndex)` path.

## Generated-only EVM results

All runs use a normal generated ZIP fixture through AS0 -> ZI0 -> DI0 -> the
copied ordinary-CREATE coordinator and the copied bounded public-API Go driver.
No raw class ABI input or decoded-page injection was used. Full transient worlds,
including LevelDB, remain ignored under `build/java-diff-mc-properties-*`; the
archive holds fixture sources/classes, recipe, artifact pins, final public opaque
checkpoints, canonical final receipt, and receipt-sequence hashes only.

| fixture/path | result |
|---|---|
| construction + Class literal + arraycopy, direct q4096 then fresh reopen | canonical `VOID`, epoch 1, 73 Java / 4 internal steps, max call gas 15,937,005 |
| storage/default/type/alias/grow/remove/NPE probe, q7 then reopen | canonical `VOID`, epoch 409, 2859 Java / 9 internal, machine root `0x56fa970bcffa3cfbe17037d7fbac4970a0981b331ce50d5a0254515a32e12b22` |
| same storage probe, q1 then reopen | canonical `VOID`, epoch 2859, same machine and VFS root as q7 |
| caller ZIP supplies `java/util/Properties.class` | refusal selector `0x6a23ad80`, ABI words `(1,1)`, root unchanged |
| large storage probe direct q4096 | preserved refusal `LC0ControlError(7)` selector `0xf15d7343`, word `7`, at 73,442,066 gas; no Head published |

The q1/q7 final checkpoints differ because their checkpoint epoch/history differs,
but terminal machine root, VFS root, artifact root, configuration root, lifecycle,
Java/internal totals, guest sentinels, and DI0 range/hash agree. The copied driver
strictly re-encodes each coordinator result and nested checkpoint event before it
writes receipt metadata. Final receipts and sequence commitments are under
`evidence/java-evm/minecraft-entry/properties-preflight/runs/`.

The direct refusal is generated-test pressure only, not a reason to raise gas,
frames, quotas, or to bypass a constructor. It is distinct from the parent-measured
original20 frontier (14 physical frames and 97,161,371 gas on the last successful
slice). This worker did not run that original world. In particular, this evidence
does **not** establish that `PropertiesUtil` reaches `Properties.<init>`, that
`LoaderUtil.findResources` runs, or any Minecraft startup/Done claim.

## Reproduction

From this worktree, rebuild the archived guest classes and Solidity artifacts with
an absolute fresh TMPDIR (if `/tmpquota` is unavailable, record the alternate
absolute scratch path):

```sh
TMPDIR=/tmp/mc-properties-bootstrap-rebuild python3 evidence/java-evm/minecraft-entry/properties-preflight/bootstrap/build_bootstraps.py
TMPDIR=/tmp/mc-properties-bootstrap-rebuild python3 evidence/java-evm/minecraft-entry/properties-preflight/fixtures/build_fixture.py
(cd evidence/java-evm/minecraft-entry/properties-preflight/engine && NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules node build.js)
(cd evidence/java-evm/minecraft-entry/properties-preflight/coordinator && NODE_PATH=/home/user/evm-jvm/geth/jvmevm/runtime/node_modules node build.js)
python3 evidence/java-evm/minecraft-entry/properties-preflight/run_generated.py --probe construction --quantum 4096
python3 evidence/java-evm/minecraft-entry/properties-preflight/run_generated.py --probe properties --quantum 7
python3 evidence/java-evm/minecraft-entry/properties-preflight/run_generated.py --probe properties --quantum 1
```

The runner has one 20-minute deadline over Go build plus all child public EVM
calls; it uses a 4096-resume guard and file-backed logs. Parent must independently
rebuild/replay and only then choose whether to start a **new** original20 world
with fresh pins.
