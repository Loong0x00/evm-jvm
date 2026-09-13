**DEFERRED by the latest user Minecraft-first directive; no helper worker assigned.**

# Go-only phase audit helper interface for parent step-wise transport

Target is immutable MR0 engine/coordinator and accepted AS0/ZI0/DI0. No Solidity,
profile/cap/ABI/core changes. Helper is appended as a separate package-main Go
file beside a legitimate owned COPY implementation; no accepted/private Session
reach-through, host ZIP/class parser/inflater/evaluator or page injection.

Signature: `func phaseAudit(e *env, update bool) (json.RawMessage, error)`.
Existing env/m/ABI/pins/view helpers are from stages-preflight driver. Parent adds
ONLY `PhaseFacts json.RawMessage` to manifest, JSON name `phaseFacts`. `update=true`
is called after a successful actual EVM mutation and before its matching persist,
and once for first atomic factory. It derives and stores stable EVM facts, phase,
index root, decoder sizes/final roots, coordinator bindings. `update=false` is
called during Open; compare exact stable facts/metadata and return error, never
repair metadata or silently adopt new bindings. Read-call observation counters may
advance, but no authority publication. Only actual public EVM ABI reads plus exact
code/nonce observations of the owned StateDB; no class/ZIP interpretation.

Required phase strings: input-open (AS0 unsealed, any cursor including full-but-
unsealed), as0-final, index-bound (ZI phase0), index-scan (ZI phase1), index-final
(ZI phase2/no decoders), di0-live (any decoder not FINAL), resources-final (all
registered decoders FINAL, regardless of whether caller intends more), coordinator-
ready (coordinator exists, no Java checkpoint), java-running, java-terminal.

Parent owns a NEW per-operation driver. Every public step performs <=one mutating
CALL/CREATE, registers any new route/name BEFORE phaseAudit+persist, then returns;
next process reopens EVM cursors. No class/ZIP host catalogue. Requested names are
caller-supplied binding assertions (the test fixture lists them), not archive data.
Only create another DI0 after all already-created resources FINAL. Class selection
binding becomes immutable at ordinary coordinator CREATE. Bad entry0 can fail then
same package good entry1 starts after fresh Open. Parent removes old pre-set
java-running before Start: applyDecoded chooses phase after actual EVM success.

Audit requirements:
- exact engine code/address/nonce0 and AS0 route ownerNonce0 CREATE; ordinary owner
  nonce equals1+indexPresent+decoderCount+coordinatorPresent, no hidden controller.
- AS0 owner, declared length, cursor/page-count consistency, sealed/content,
  immutable chain bounds. InputLength1..32MiB. No initial fake Java anchors.
- ZI exact address/code, owner/store/content/length dependencies; phase0/1/2,
  CD/count/next/cursor/rolling/root consistency and admitted caps. IndexRoot zero
  until actual FINAL; don't label phase-final before EVM finish.
- DI exact sequential address/code/owner/index/indexRoot/store/content/nameHash,
  plainSize<=262144 (DI bound DOES NOT widen Java), phase1..4, work, output/input/
  page counters/rollings/final-root/pending state consistent with accepted kernel
  bounds. Store stable progress facts. Correct per-slot sizes and zero pre-FINAL
  resource roots. Names unique/valid raw class binding, max4 registered decoders.
- Coordinator exact address/code, owner/index/finalRoot/classCount/total<=65536,
  public classBinding against all fixed slots; recompute package and instance
  commitments from immutable source domains and fixture salt, not guessed IDs.
- No coordinator implies zero package/instance/coordinator code/total. No Java
  means epoch/slices/JVM/internal/machine/VFS/checkpoint/result/exception/seed/
  artifact/config/runtime fields all zero, never invented. With Java validate
  canonical public engine head vs all existing bound roots/epoch/lifecycle and
  checkpoint SHA/Keccak bytes. Any unavoidable Java payload semantic limitations
  explicitly label, no host JVM decoding/evaluation.
- Return ordinary errors (recover internal must panic if needed); do not publish
  during validation. Parent closes LevelDB/trie on all Open rejection paths and
  performs cheap metadata/paths/phase/route checks BEFORE opening LevelDB too.
- Stable facts exclude wall time/PID/host counters and file paths. Don't credit
  successful future fsync on persisted Head or invent IO when reopening.

Parent independently tests/reviews; helper compilation or worker report is not
acceptance. Existing worker complete-command positive proof is insufficient: parent
actually terminated after first durable input/index mutation; subsequent public
resume fails. Each accepted durable mutation must represent a valid re-openable
phase, not just the end of a monolithic high-level command.
