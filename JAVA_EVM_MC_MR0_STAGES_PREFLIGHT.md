# MR0 pre-Java lifecycle and atomic-initial-state COPY preflight

Status: **unaccepted Go-only COPY experiment** based on `752e9d56d`. This is a
transport/public-API foundation, not an MR0 Session/profile acceptance, a JVM
claim, Selected merge, or Minecraft execution.

## Scope and invariant

The candidate is retained only at
`evidence/java-evm/main-root/stages-preflight/transport/mr0_stages_session.go.txt`.
It uses a normal owned LevelDB/StateDB world and public EVM CALL/CREATE routes;
it does not reach an accepted Session, use reflection, inject StateDB/cache
authority, parse ZIP/classes, inflate, or evaluate Java on the host.

The source starts from the parent-repaired atomicity COPY, not the older worker
copy. It retains the parent repair for cancellation output clearing, poisoned
unreadable prior Head, and non-speculative manifest directory-sync accounting.
The immutable engine and coordinator pins remain respectively
`5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875` /
`0x2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f`
and `0x06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c`.

`factory-initial` intentionally has no empty persisted Head. It stages exact
LOCAL engine code at `0x4d52304d41494e454e47494e4500000000000001` nonce zero
and the ordinary AS0 CREATE from the fixed owner nonce zero, then publishes one
first root. A manifest-create failpoint leaves no `durable-head.json`; Open has
no initial-install fallback. The first legitimate reopen is `input-open`, with
engine/AS0 routes and no index, decoder, coordinator, package, instance,
checkpoint, CP, or Java anchor.

## Public phase operations

The COPY exposes durable operations rather than a monolithic `setup` flag:

1. `factory-initial` then `verify-initial`;
2. opaque AS0 input append/seal (`as0-input`);
3. EVM ZI0 discovery/scan/final (`index-scan`);
4. durable DI0 work-one prefix (`di0-live`) then EVM-only FINAL publication
   (`di0-final`);
5. constructor-fixed package coordinator (`package-ready`);
6. `start-ready` only after the ready Head is reopened.

Each pre-Java Head carries an explicit phase and rejects invented Java/checkpoint
anchors. The opaque input SHA-256/length binds later append operations but grants
no decoded-page or archive authority. Fixture names are only generated binding
assertions; the execution path does not discover names from the archive. Current
pre-Java route checks are deliberately narrower than the eventual per-phase EVM
getter/recursive-link validation.

The current source supplies a generated positive fixture proof through the
operations above and the first running slice. It does **not** yet prove all
required phase-dependent getter/recursive-link/counter validation, BadMain
same-package refusal, terminal positive matrix, strict 427 receipt adaptation,
or the full new-phase fault/CAS/capacity matrix. Those omissions are deliberate
and must not be masked by calling this a complete Session.

## Reproduction

Run only into a new ignored scoped path:

```sh
python3 evidence/java-evm/main-root/stages-preflight/reproduce.py \
  build/java-diff-mc-main-root-stages-NAME
```

The recipe uses one 20-minute functional deadline and scoped absolute `TMPDIR`.
It deliberately does not use `start_new_session` or GNU `timeout`, and it makes
no whole-process-group RSS claim. It records the factory failure/no-Head check,
each fresh-process phase Head, source/input hashes, and the result summary under
the ignored output. Parent must independently rebuild/replay before any review.

No Solidity/artifact/ABI/quota/accepted-core change, original JAR handling,
Minecraft execution, EULA/listener/world/Done claim, settings change, or push is
part of this preflight.
