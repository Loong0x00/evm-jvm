# Bounded `Array.newInstance(Class,int)` candidate

Status: **UNACCEPTED candidate; parent independent review/build/replay and fresh original131 gate still required.** No original Minecraft JAR/classes/resources/worlds/receipts or parent/performance-review evidence was read or used. All guest execution inputs here are locally generated Java 8 fixtures.

## Source and build

- Source base: accepted P52 commit `98ca72b9853aa6d02d028c730c9f9f907ebf17bb`; its source-only manifest and all nine listed files were SHA-256 checked before editing (`base-source-manifest.json`, `base-pins.json`). No mismatch or extra base files.
- Candidate source: `engine/MCEntryInterpreter.sol`. Java 8 SDK emitted the 477-byte bootstrap `java/lang/reflect/Array` image from `java/lang/reflect/Array.java`: private constructor; public ordinary-Code `newInstance(Class<?>,int)` wrapper; private static native `newArray(Class<?>,int)` exactly `0x010a` and descriptor `(Ljava/lang/Class;I)Ljava/lang/Object;`.
- Append-only bootstrap: leaf116 added after the exact P52 0..115 prefix; recomputed 117-leaf root is in `root.json`. The raw-150 fixture places `Component` at guest class index149; this makes actual array leaf metadata `0x100 + 149 = 405` (>255), then exercises a guest `aastore` and receives genuine `ArrayStoreException` (kind9). With 150 raw classes plus117 bootstraps the checked program count is267; Array is bootstrap slot266.
- Native global binding22 only; prior global1..21 branches and String-local12 source are unchanged. Raw `java/lang/reflect/Array` is reserved. Candidate coordinator hash was updated to this actual engine runtime hash; no coordinator ABI/storage change.
- Compiler outputs and exact pins are in `engine/`, `coordinator/`, `candidate-pins.json`. Engine init/runtime are 435030/435002 bytes, below existing LOCAL1M cap. No accepted resource, EVM gas, ABI, storage, checkpoint schema, or consensus limits changed.

## Fresh geth-EVM generated-fixture results

The local test runner invokes the candidate's real Solidity runtime through geth `core/vm/runtime`; it does not execute guest classes on the host. `final-gates/` preserves each final run. JVM quantum 1/7/65536 on the poison-`<clinit>` zero-length component fixture all reached guest `Done`; machine-state root was identical across quanta (`eb059c2c8d9f8107ff61c4d901f7efe394e683aeba504493d68dfaa4f09111cf`). This also shows array creation did not initialize the component.

The 150-raw-class high-index fixture reached the same terminal `ArrayStoreException` kind9 at q1/q7/coarse, with identical machine root `3a0abeacb5519edea0b75f834e0c56366318343eefc4aff8ccd9c99ec3e9e16a`.

Other final generated probes: interface component and private abstract component arrays complete; two zero-length calls produce nonidentical arrays; dense reference array casts/stores, aliases, shallow clone and default-null slot checks complete; length65536 completes with a 526902-byte checkpoint; length65537 produces Java OOM kind7; null component plus negative length yields NPE kind6; valid Object component plus negative length yields NegativeArraySizeException kind4. Unsupported primitive/array-valued class literals, unsupported `(Class,int[])` overload, and raw owner are EVM refusals, not fake guest values. Exact outputs/selectors and all run metadata are preserved in logs.

A retained generated P52 control for `Class.getName` and `System.arraycopy` reaches Done. EnumSet control passes when the generated enum is first genuinely initialized; the uninitialized-enum attempt is preserved separately and refuses under the existing already-published-enum profile.

## Corrections and remaining gates

An initial candidate shifted P52 tail parser assignments by one after adding the leaf. That version and its build/test evidence are preserved under `attempts/pre-tail-parser-fix/`. Corrected final parser indices are `count-12..count-8`, preserving actual image slots105..109; EntrySet110 and ArrayList Itr115 remain fixed. Final outputs were rebuilt and the generated gates above rerun against them.

Not run: separate-process durable checkpoint reopen, a persistent coordinator package/session, full heap-record decoder comparison, and parent fresh original131 gate. These remain independent parent handoff requirements; this report makes no acceptance or Minecraft-readiness claim.
