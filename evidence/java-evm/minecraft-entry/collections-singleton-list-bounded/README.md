# P55 independently parent-verified true singleton list

Parent preserved the compiler cliff/wrong119-layout evidence, adopted only the canonical-config memory encoding refactor, and independently rebuilt the correct120-class layout. A generated EVM probe found missing Java8 RandomAccess/Serializable markers on the returned helper; parent corrected those two existing marker links and reran fresh current-artifact gates.

Current root08d8a3019da084226f5d4c0e60d8f0f450bc0421aa7f04da031314e05070252a; engine441562B SHAf0506373cdad2daeb97216629f949653edefcacc9ec0471e8f8a14dafe10f348; coordinator5411B SHA2fa5eff126cf957f772c4fb3e39847c395e2c2b08148a07414e62effb1128688. All117 old image bytes/order remain exact. Current compiled-EVM config roots match independent old13-field flat ABI encodings, including the original136 case;512 generated ABI vectors also pass. ABI/storage/codec/resource/geth rules are unchanged.

Genuine stored one-element/null/array-as-object state, independent iterators, native22/tail controls, raw150class270/highprivate269, atomic boundaries and separate-process reopens passed. Fresh original136 created actual list+iterator and advanced to missing original Iterators$7; no Cartesian product/full Collections claim. Proof `../parent-collections-singleton/`; root doc `JAVA_EVM_MC_COLLECTIONS_SINGLETON_PARENT_PREFLIGHT.md`. Historical worker receipts below refer to the pre-marker-correction candidate, not these fresh artifact bytes.

---

## Historical worker report

# Bounded Collections.singletonList candidate (P55)

This is an **unaccepted local candidate** for the measured Java 8 `Collections.singletonList(Object)` call only. It supplies the ordinary generic factory, a stored-element immutable list with true size/isEmpty behavior, fresh independent one-element iterators and genuine exhaustion. It does not implement the broader `Collections`/`List` API.

`coordinator/MCEntryInterpreter.sol` is an early accidental source copy preserved as an attempt; no build script reads it. The canonical interpreter source is only `engine/MCEntryInterpreter.sol`.

## Provenance and pins

- Base: `bebd4be5bf5cd1c7e2df1f933c090d4a033e1e19`; accepted guest-code base `14449892eb7ac543b61e79e68b4b753149577fab`.
- Before compiler work, all 15 inputs in `../collections-singleton-source-base-p54/source-manifest.json` were size/SHA-256 verified. That directory contains source-only material; no original Minecraft payload, parent review or performance-review input was used.
- Engine bootstrap count is 120. The exact old 117 leaves are unchanged; new leaves 117–119 are Collections, Collections$SingletonList, and Collections$SingletonIterator. Reflect Array remains leaf 116. The source-derived root is in `pins.json`.
- Engine and coordinator are built only by their pinned scripts with solc 0.8.30, optimizer 200, viaIR, Cancun, metadata off. External ABI and storage layouts compare byte-for-byte with the source-only P54 artifacts.
- `_configRoot` uses a 13-field internal memory tuple. The SHA3 preimage is the byte-identical prior flat ABI tuple (skip only `abi.encode(struct)`'s leading dynamic offset word); 512 generated ABI-vector cases pass. This is a compiler-stack relief, **not** a protocol or wire change.

## Reproduction

Run from this repository root with the pinned local dependencies:

```sh
export NODE_PATH="$PWD/jvmevm/runtime/node_modules"
cd evidence/java-evm/minecraft-entry/collections-singleton-list-bounded
node engine/build.js
node coordinator/build.js
cd "$OLDPWD"
GOTOOLCHAIN=local GOPROXY=off go build -o evidence/java-evm/minecraft-entry/collections-singleton-list-bounded/build/canonical-driver evidence/java-evm/minecraft-entry/collections-singleton-list-bounded/canonical-driver.go
```

Java inputs were compiled only as build/test fixtures with `/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none`; they were never host-executed. The minimal `bootstrap/java/util/*.java` hierarchy files are compiler inputs only; the actual EVM bootstrap images still come from the pinned interpreter. Generated class input is the unchanged fixture classfile, stored in a ZIP for the accepted EVM ZIP/DI0/VFS path. For a representative positive q1 run:

```sh
D="$PWD/evidence/java-evm/minecraft-entry/collections-singleton-list-bounded"
MC_ENTRY_BINDINGS=SingletonListProbe.class "$D/build/canonical-driver" setup-chain "$D/build/repro-q1" "$D/coordinator/MCEntryCoordinator.json" "$D/engine/MCEntryInterpreter.json" "$D/build/fixture.zip" 1
"$D/build/canonical-driver" finish "$D/build/repro-q1" "$D/coordinator/MCEntryCoordinator.json" "$D/engine/MCEntryInterpreter.json" "$D/build/fixture.zip" 1
"$D/build/canonical-driver" verify "$D/build/repro-q1" "$D/coordinator/MCEntryCoordinator.json" "$D/engine/MCEntryInterpreter.json" "$D/build/fixture.zip" 1
```

Keep observer logs outside a world directory: Session reopen strictly rejects unrelated files inside that namespace. Each invocation should use a new world directory. Full fresh q1/q7/q128, retained-control, raw-refusal and actual-150-class runs are summarized in `build/reports/verification-report.json`; all original attempts are preserved rather than overwritten. The high-index inputs are reproducible with `build/generate-class-boundary.py` followed by `javac -source 8 -target 8 -g:none -d build/class-boundary/classes build/class-boundary/src/*.java`; the script packs those 149 classes with the unchanged singleton probe. `build/class-index-audit.py` decodes the actual terminal EVM checkpoint and reports 270 class entries (maximum index 269) for the 150-raw-class positive run.

## Results and limits

- Generated positive probe completed via genuine guest `main`; q1/q7/q128 have the same machine root, VFS root, total Java/internal steps and successful terminal outcome. Fresh-process durable reopen passed for each. Outer EVM gas/call counts differ by quantum; no performance claim is made.
- The positive probe covers ordinary object and `null`, an actual zero-length `Object[]` as one list element, `List`/`Collection`/`Iterable`, iterator identity/state, independent instances, and real `NoSuchElementException` exhaustion.
- A 150-raw-class bundle completed through the actual EVM path with checkpoint count 270 and bootstrap class indices 267–269; it is not an arithmetic-only calculation.
- `add`, equals/hashCode, typed `toArray`, `List.get`, `Iterator.remove`, and `Collections.emptyList` probes produce raw `CallError` refusals with unchanged Head/root; they are not Java results and do not become AME/UOE/default values. Explicit `native` declarations are retained where required by minimal Java source interfaces.
- Retained read-only controls for Array reflection, ArrayList capacity/typed-array/iterator, HashMap empty entry view, Function.apply and NavigableSet class-literal bootstrap passed. An additional ArrayList.add control failure (`CallError(4,44)`) is preserved and is outside this change; no unrelated API was repaired.
- This candidate is not independently accepted, is not an original Minecraft execution, and is not pushed.
