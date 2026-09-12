# MR0 direct-main COPY preflight

Status: **DISPOSABLE COPY implementation compiled; no EVM execution gate or acceptance.**
Base is `343b55537eee00730c36382529353a78a471f5e5`; implementation evidence is
`evidence/java-evm/main-root/preflight/`. Accepted CB0/VFS0a/JVM/core code and
artifacts were not changed.

## Isolated ABI/schema

The copied, domain-separated `MR0MainCoordinator` exposes `startMain(bytes32,uint8,uint64,uint32)`
and `resumeMain(bytes32,uint64,bytes32,bytes,uint64,uint32)`. It has no old
`start`/`resume` selector. It retains the constructor-fixed single FINAL ZI0/DI0
route, owner/package/CAS checks and <=4096 DI0 reads from CB0's copy. The copied
engine exposes `startMain(bytes32,bytes[],string,(bytes,bytes,bool)[],uint64,uint32)`
and `resumeMain(bytes32,uint64,bytes32,bytes[],bytes,uint64,uint32)`.

The sole root is schema 1, kind 1 `MAIN_EMPTY_STRING_ARRAY`, exact `main` and
`([Ljava/lang/String;)V`, with commitment
`keccak256("JVMEVM:MR0:MAIN:EMPTY-STRING-ARRAY:1")`. The prelude magic is `MR01`;
it serializes kind and commitment. Config commits the same domain/kind/name/
descriptor/commitment. Root resolution matches name **and** descriptor, allows
other overloads, and refuses duplicate exact matches and non-public/non-static,
native, abstract, synchronized, missing-Code or unsupported roots.

The public slice tag is `1 RUNNING`, `2 VOID_TERMINAL`, `3 JAVA_EXCEPTION`.
The retained legacy integer field is zero for main and is never a Java return.
The engine creates an ordinary rank-one, String-leaf, zero-length array in the
existing heap, puts its nonzero handle in local 0, and validates that precise
array identity/type in frames/checkpoints. Decode uses the serialized heap/local
rather than allocating a fresh root array.

## Measured build

Pinned solc is `0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, viaIR,
Cancun, metadata off. The isolated engine is 295568 runtime bytes (SHA-256
`5210271ce941ab322293ada29a551c30c1ac587eb5ab77538d8849025eb850d2`, Keccak
`463dd2419b296aa39f766bdae06d11b49b9cffa935d052a38fe82921757e29de`) and is
below the explicit 320 KiB disposable cap. Its 295596-byte init is **not** an
ordinary CREATE claim. Coordinator runtime is 3547 bytes, init 7381 bytes,
Keccak `b4785137ec9ccde676a5892b602a303e29356c14c7d6ca19db561d9526dfb67c`.

Generated Java 8 sources cover a void positive with `String[]` instanceof,
static initialization/cross-call and retained identity; and an uncaught
exception. The separate Oracle is excluded from ZIP creation. Fixture hashes
are in `raw/fixture-build.json`.

## Remaining blocker

No public-only Go transport/driver copy has yet installed the isolated engine,
created AS0/ZI0/DI0 resources, or made a real EVM call. Thus there are no actual
positive direct/q1/q7 results, gas, checkpoint/root, disk/process, terminal,
CAS/publication/retry, boundary, or refusal receipts. These are explicitly not
claimed. Parent reconstruction/replay must supply such a driver and independently
validate the copy before any profile promotion or acceptance.

No official archive/class was handled; no Minecraft/EULA/listener/world/Done claim.

## Parent source review before execution (not runtime findings yet)

Integrated as0acc0c72d/fa33e828e/b24d5ff40. Compilation is not an execution gate.
Parent found source/document mismatches that MUST receive actual EVM controls:

- `_prepare` still selects by method NAME only, despite the above exact-descriptor
  overload claim. `_loadRoot` checks the descriptor only after name selection;
  an otherwise valid main overload may therefore be rejected as duplicate.
- `_validateMainRootLocal` requires local0 to remain a non-null empty String[] at
  every pending checkpoint. Java may legally rebind its args parameter or reuse
  its local slot. A direct return can bypass that depth!=0 check while a small
  quantum exposes it. Input shape is not permission to freeze a mutable local.
- The actual ABI component remains named `result`; documentation calls it
  `legacyIntResult`. Transport must use the actual ABI, expose explicit outcome
  tags and never report reserved zero as a Java int return.
- ROOT_ABI.md's statement that publication errors are reverts is not a Go IO rule:
  production-style publication failures must expose gas only, no EVM revert or
  usable slice/checkpoint/root/log. Do not fabricate a revert for filesystem failure.

A scoped Go-only transport worker now builds real EVM tests against the EXACT
compiled candidate, preserving these potential refusals without Solidity edits.
Selected-table optimization has a different sole Solidity writer/worktree; no
concurrent MR0 semantic patch is authorized. Parent will independently replay
before deciding repairs. Accepted source/quotas and original JAR remain untouched.
