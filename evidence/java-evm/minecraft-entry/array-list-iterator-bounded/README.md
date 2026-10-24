# P52 independently parent-verified ArrayList.iterator

Parent independently rebuilt the exact old and new Java8 images, engine/coordinator and driver, verified private owner/cursor/size/backing state (including misleading public size override), retained actual tail slots, high-raw private helper class265, atomic refusal and separate-process reopen, then ran a fresh original131 package. No parent guest-semantic correction was needed. Nonempty iteration, mutation and fail-fast remain unclaimed.

Current116-image root `c1b50cfbeb974b541531c6f931ddc5ebc42b6047779525bfb99a72618848e97b`; engine431490B SHA4a25323e450c256efeee6a41519166a06c908beb8812dceca2c1e6c44238866a. Parent proof: `../parent-array-list-iterator/artifacts/reflect-array-newinstance-blocker.json`; root doc `JAVA_EVM_MC_ARRAY_LIST_ITERATOR_PARENT_PREFLIGHT.md`.

---

## Historical worker report

# Bounded genuine `ArrayList.iterator()` candidate

Worker-only implementation/evidence on branch `java-array-list-iterator`, based on
P51 source-only commit `2419d7de64f6b2f75b80e161a4464a83c18868fc` and accepted
GuestCode `9bf0cdfc61e539225c3b4a494a325b72cd58f98d`. **Independent parent
review/build/acceptance is pending.** This is not Minecraft readiness or general
`ArrayList` conformance.

## Scope

- Replaces only the existing `java/util/ArrayList` bootstrap image at leaf 98.
- Appends exactly one private `java/util/ArrayList$Itr` image at leaf 115 (116 total).
- `iterator()` is ordinary Java bytecode constructing a new owner/cursor helper.
  `hasNext()` reads the private owner `size` through javac's ordinary synthetic
  `ArrayList.access$000`; `next()` checks the same private field, throws the real
  `NoSuchElementException` when exhausted, and reads private `elementData` plus
  cursor in ordinary bytecode on the nonempty path. The private helper's `remove()`
  remains a native declaration without a binding. No iterator native was added.
- Test overrides public `size()` to return 7; actual EVM `hasNext()` remains false
  for its genuinely empty owner, proving it reads the private storage field rather
  than a constant, capacity, or overridable method. Default, capacity-0 and
  capacity-3 empty owners, fresh iterator identity, typed `Iterator[]` clone,
  exhausted `next()`, null receiver, and wrong cast all execute in the EVM.
- `add`, growth, `get`, `toArray`, equality/hash, clone, and raw helper replacement
  remain unsupported and tested as atomic guest/EVM refusals. No mutator, fail-fast,
  concurrency, or populated-list iteration claim is made. Since admitted mutations
  are absent, this is only the requested single-thread cursor/owner profile.

## Pinned layout and limits

The source verifier checks all 16 P51 source-manifest files first. All old bootstrap
leaves except 98 retain their exact byte/order commitments; the appended helper is
leaf 115. The fresh `DBOOT` root is `c1b50cfbeb974b541531c6f931ddc5ebc42b6047779525bfb99a72618848e97b`.
All nine engine profile domains and the four coordinator domains use this profile's
fresh literal. The coordinator authenticates the actual new engine runtime hash.
The `count-11` through `count-7` tail assignments preserve program slots 105-109;
HashMap EntrySet remains at slot 110 and the new helper is appended after the old
ListIterator slot. No class-count/raw-byte/runtime/checkpoint/gas/frame/quantum/native
or other EVM limits were widened. See `pins.json` for byte/hash/runtime details.

The engine artifact is LOCAL preinstalled-code evidence, not standard `CREATE` or
EIP-170 deployment compatibility. Runtime is 431,490 bytes, below the existing
1,048,576-byte local ceiling; the coordinator runtime is 5,411 bytes.

## Reproduction and evidence

Pinned Java 8 compiler: `/usr/lib/jvm/java-8-openjdk/bin/javac`, source/target 8,
`-g:none`. Pinned Solidity compiler/build settings are encoded in each `build.js`;
Node dependencies resolve only with:

```sh
NODE_PATH=/home/user/evm-jvm/array-list-iterator/jvmevm/runtime/node_modules
```

Build/recreate source classes, engine/coordinator artifacts, fixture archives and
local Go runner sequentially with `./build-candidate.sh`. Then run
`NODE_PATH=... python3 ./verify-candidate.py`. The latter verifies the base manifest,
Java bytecode/class images, leaf commitments, artifact hashes, tail slots, current
EVM receipts and immutable quotas; it does not access any original Minecraft input.

Generated Java 8 fixture only, fresh local geth EVM, ordinary coordinator and separate
setup/resume/reopen processes:

- `runs/iterator-final-001/`: q1, q7 and coarse q128 all complete with 416 Java steps,
  lifecycle `Done`, matching machine/VFS roots, and quantum-dependent opaque
  checkpoint hashes. Detailed final-head and process evidence is in each `q*/`
  and sibling `reports/q*/` directory; logs are under `runs/logs/`.
- `runs/iterator-refusal-final-001/`: q1 refusal receipts for each unsupported
  operation and for raw replacement of the private helper. All tested refusals keep
  root and durable Head unchanged.
- `runs/candidate-verification-report.json` and `pins.json` are the concise receipt
  index and immutable image/artifact pins.
- Earlier failed/revised attempts remain under their original `iterator-smoke-*` and
  `iterator-refusal-*` names. Do not treat the smoke run as final: it preceded the
  last domain/codehash rebuild. The failed raw-helper `finish` attempt is retained;
  its setup had already refused atomically before any session existed.

The `next()` non-exhausted element-read path is confirmed by source and javap, but
cannot be reached by an admitted Java fixture because every list mutator remains
unbound. Nonempty iteration requires its own future measured scope. No Minecraft
JAR, classes, resource payloads, worlds, or original execution receipts were read or
included.
