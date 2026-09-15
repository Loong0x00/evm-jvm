# BENCHMARK_RESULT — measured raw-class cap 29→30

## Result

Implemented **only** the measured raw-class count29→30 increment on top of the accepted
parent-3ed302a92 EnumSet baseline, inside an isolated worktree and with generated
fixtures only. The parent-amended EnumSet engine is preserved byte-for-byte except the
mechanical delta: nine equal-length domain strings, `MAX_RAW_CLASSES = 29 → 30`, and one
`uint32(29)` config word. The coordinator is preserved except its three domain strings,
four fixed arrays `[29] → [30]`, its `n > 29 → n > 30` guard, and the fresh anchored
address/codehash pins. All 83 bootstrap images/order, the 12 native bindings, raw-byte
262144, 25,000,000 commit reserve, 1,000,000,000 LOCAL gas, 128 frames, 1 MiB checkpoint
and 32 KiB head bounds are inherited unchanged from the parent.

Fresh equal-length LOCAL384 identity (declared and pinned, no old parent strings left):

- domain `MC-ENUM-SET-PARENT3`, address `0x4d432d454e554d2d5345542d5033000000000001`
  (`MC-ENUM-SET-P3`), owner `0x4d432d454e554d2d5345542d4f33000000000002`
  (`MC-ENUM-SET-O3`), diagnostic total-class bound **113** (raw30 + 83 images).
- engine **393205 B ≤ 393216 B** (11 B headroom, unchanged from the parent size),
  runtime SHA256 `03fb5a308187f091b653f4f432453f1d62726bb9f54d0febe2e9f24853270ca4`,
  Keccak `1ecd7082cd5578556cc17f6a082eccb224780ba316e1fe3edb90cd217a943d7d`.
- coordinator **4146 B**, runtime SHA256
  `fa0ef28517fe39ecf67b52eca79c14c8d6f11a77dbbc61f090a59b9f72891b67`, Keccak
  `9ecc340d36da5e85e113ef90a27b80998cd79659702fa32795341362989064c1`.

Single heavy source build (engine + coordinator + driver), single complete generated
gate run, plus one parent-EnumSet semantic regression replay. No original Minecraft
JAR/class/resource/world was read; no Minecraft/Done claim; no network, no push.

## Files Changed

Source commit (`evidence/java-evm/minecraft-entry/classcount30-preflight/`):

- `engine/MCEntryInterpreter.sol` + `engine/build.js` — cap30 engine source and the
  unchanged official cap-checked build script.
- `coordinator/MCEntryCoordinator.sol` + `coordinator/build.js` — widened arrays/guard,
  fresh address and engine-codehash pin.
- `tools/stage.py` — deterministic parent→cap30 staging (replacement counts asserted).
- `tools/build.py` — reproducible build/verify orchestration (one engine build).
- `tools/verify_source.py` — strict reverse verifier pinned to parent-3ed302a92.
- `tools/generate_fixtures.py` — generated-only Java8 count fixtures.
- `tools/gate.py` — generated cap30 gate (29/30/31/boundaries/reordered/canonical).
- `tools/checkpoint_diagnostic.py`, `tools/verify_receipts.js` — READ-ONLY transport
  diagnostics and canonical receipt verifier (bound 113).
- `tools/Go.txt` — driver rebased from the accepted parent driver to the fresh
  domain/addresses/hash pins and `> 30` transport guards.
- `tools/archive.py`, `pins.json`, `parent-input.json`.

Evidence commit: `artifacts/**` (62 hashed files: build/gate logs, engine+coordinator
artifacts, fixture receipts, per-world durable heads, command receipts, canonical
receipts, reverse-verifier output, EnumSet regression, `SHA256SUMS`, `manifest.json`)
and this `BENCHMARK_RESULT.md`.

## Verification

- `tools/verify_source.py build/java-diff-mc-classcount30-source-build` passes: parent
  input SHA256s; engine/coordinator/driver equal the parent text plus **only** the
  mechanical replacements (counts asserted: 9/3/5 domain, 1+1 engine cap spots, 4+1
  coordinator arrays/guard, 2 driver guards); 83 ordered bootstrap images byte-identical;
  binding ids 11/12 and EnumSet image SHA preserved; diagnostic `classes<=113`;
  built-artifact bytes/SHA/Keccak equal `pins.json`; sizes 393205/4146.
- Uniform build: `tools/build.py` exit 0 (engine build ≈247.6 s; gofmt/go build/go vet
  clean), coordinator probe builds confined to disposable gate output.
- `tools/gate.py` exit 0, **42.09 s**, generated-only:
  - exact 29 and 30: q1/q7/direct + fresh-process reopen + canonical inspect (all raw
    classes fully initialized, checkpoint decoded and class count == n+83); quantum
    invariance of `machineRoot`/opaque payload. 29 → epoch 116, 116J/2I, machine
    `0xa438817b…`; 30 → epoch 120, 120J/2I, machine `0x6df406a5…`.
  - reordered 30 bindings: accepted, distinct package root, all classes canonical.
  - **three independently reached 31-class atomic refusals**: product driver
    pre-mutation panic (no world dir created); product coordinator `MR0Error(2)`
    (`0xab23ed08`, words `[2]`, root unchanged); product engine `LinkError(1,31)`
    (`0x427cfac5`, words `[1,31]`, root unchanged) reached only through a disposable
    widened test coordinator.
  - **262144**: coordinator accepts the exact aggregate and the pinned engine refuses
    honestly inside its parser (`LC0StateError(1,0)`, `0x71540d20`, words `[1,0]`,
    root unchanged, 895.16 M gas) — no silent acceptance, no cap fabrication.
  - **262145**: atomic coordinator aggregate refusal `MR0Error(12)` (`0xab23ed08`,
    words `[12]`, root unchanged).
  - canonical receipts: 273/273 verified over the six successful worlds (nested ABI,
    events, CP/counter chains, DI0 read ranges).
- EnumSet regression: the parent's own `enumset_gate.py` replayed against the cap30
  artifacts passes unchanged (positive 541J/11I q1=q7=direct, errors 27J/7I, failed
  94J/10I, uninitialized bounded refusal, raw-replacement `BootstrapProfileError(1,1)`).
- Evidence integrity: `sha256sum -c artifacts/SHA256SUMS` clean; `artifacts/manifest.json`
  lists all 62 files.

## Remaining Uncertainty

- The genuine `org/apache/logging/log4j/util/Strings.class` (3283 B, SHA256
  `497317f6…`) append and the unchanged original30 run are **parent-owned** and were not
  performed here; this result covers the cap/domain mechanics and generated gates only.
- The 31-class coordinator/engine refusals are reached through disposable, generated
  test transports (widened transport/coordinator copies); only the driver-layer refusal
  uses the product driver. Those copies are never product pins; the product coordinator
  and product engine are the exact built artifacts.
- The 262144 case is an honest engine-side infeasibility observed at the recorded
  selector; it is not a claim about which internal parser bound is reached, and the
  selector set is validated against the built engine ABI rather than hard-coded.
- Fixture ZIP bytes are not committed (following the accepted classcount29 precedent);
  the receipts pin ZIP/class SHA256s and `tools/generate_fixtures.py` regenerates them
  deterministically with Java8 `javac`.
- Headroom remains 11 B under the fixed 393216 B LOCAL384 cap, so any further semantic
  edit must be re-measured; no accepted cap was changed.
