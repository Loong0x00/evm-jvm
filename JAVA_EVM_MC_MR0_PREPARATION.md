# MR0 direct-main generated preflight preparation

Status: **chosen next origin experiment, COPY ONLY, no production freeze/acceptance**.
Parent reviewed entry-origins proposal11293f2a0: accepted CB0 actually enforces one
common index/root with Error13; root `_loadRoot` actually requires exact all-I/I.
Generated guest wrappers work, but do not exist inside the exact official JAR.
Choose proposal route B0 as experiment name MR0; defer multi-origin route A0.
This selection is engineering scope, not a measured superiority claim.

## Purpose and constraints

Exercise a generated public static `main:([Ljava/lang/String;)V` directly from one
EVM-indexed archive, with a genuinely allocated non-null empty guest String[]. No
launcher class in the archive, no host arguments or class array, no altered/repacked
original JAR. No original JAR/class handling/execution is part of this experiment.
No fake integer return, banner, EULA, listener, world or Done.

Accepted CB0/VFS0a and every existing source/artifact/ABI/quota remain untouched.
MR0 copies use1..4 user classes/65536 aggregate,38 bootstraps, unchanged heap/fields/
VFS/checkpoint1MiB/CP4096/Code65535 and ordinary100M30s. Do NOT inherit the8/256KiB
capacity experiment or its1B boundary policy. Cost profiling runs independently;
MR0 does not cache/change class loading or address its density failure.

## Prototype contract to measure

- Separate domain/namespace/code pins/LOCAL address for an exact freshly compiled
  COPY engine and coordinator. Its oversized engine, if needed, is a clearly
  separate disposable initial-state installation only, never claimed accepted
  VFS0a identity/CREATE/standard-chain deployment. All resources/coordinator/pages
  remain ordinary CREATE. Runtime<=320KiB; pinnedsolc0.8.30,opt200,viaIR,Cancun,
  metadataoff, artifact/layout/maxargs independently measured.
- Prefer a main-only prototype API (`startMain`/`resumeMain`) rather than repurposing
  old int Start/Resume. Fixed main name and descriptor, immutable MAIN_EMPTY_STRING_ARRAY
  root kind and empty-args commitment; selected entry resource remains EVM-derived.
  No arbitrary string/int/bytes argument reinterpretation. Old int selectors must
  not accidentally admit the new root; old accepted int implementation is untouched.
- Root method selection must use exact name AND descriptor. A valid main overload
  with a different descriptor must not mask or duplicate the unique exact target.
  Require public/static/non-native/non-abstract and supported executable Code.
- Allocate the same genuine guest reference-array shape that accepted anewarray
  uses: length0, rank1, String leaf class, nonzero valid heap handle, initialized
  reference local0. Reuse canonical allocation/validation semantics; do not treat
  null or a host-created int slot as an empty array. Allocation uses existing
  heap quota and must not initialize an unrelated application class prematurely.
- Real root return opcode is void. Public result MUST distinguish running, ordinary
  VOID termination and genuine Java exception. Any retained internal legacy int
  storage slot is reserved/zero, not a returned Java int. A tagged main result may
  wrap existing checkpoint metadata; document its exact prototype ABI/types.
- Root kind/name/descriptor/empty-args commitment must bind config, artifact/engine
  identity, anchor and opaque checkpoint validation. They may be enforced by a
  main-only API with domain-separated config and typed envelope or an explicit
  root spec; choose the smallest unambiguous form and record exact bytes. On resume
  derive only from validated EVM state/checkpoint, never reconstruct a guest array
  from host data. Checkpoint retains the real root reference and heap graph.
- Audit root-specific assumptions in `_prepare`, `_loadRoot`, `_freshState`,
  `_restoreSelection`, `_decodeMachine`, `_validateInitAndFrames` and root return.
  Changing only descriptor admission is not enough. No broad Java/link/opcode edits.
- EVM coordinator still materializes ALL class bytes from actual FINAL DI0 reads
  <=4096 from ONE archive/index. Public normal owned/cloned transport, no reflection,
  private Session/StateDB access, host ZIP/class parser/inflater/catalogue/evaluator,
  raw class execution input, class page injection or failed-trace recovery.
- Maintain exact owner/package/CAS, one validated nested engine event, actual
  publication before success, terminal opaque checkpoint, old-root rollback before
  publication and postrename poison. Empty seed policy remains unchanged.

## Generated gates

1. One generated main sees non-null/zero-length String[], proper String[] runtime
   type (not Object[]), <clinit>, cross-call/static effects, and genuine void return.
   The guest checks invariants and throws on a mismatch. Separate Java8 TEST oracle;
   no host inspection fabricating Java state/outcomes and no int-root fallback.
2. Another main has a genuine uncaught Java exception; typed exception, not void
   success or EVM error. Demonstrate array identity and reference survival across a
   small quantum rather than rebuilding it on each resume.
3. Direct/q1/q7 root/counter equivalence, actual new-process start/resume/terminal
   read/hash, warm and memory behavior. Selected root kind and void/exception tags
   are explicitly checked at every stage, with prior published root chaining.
4. Wrong descriptors()V/(I)V/([Ljava/lang/String;)I, nonpublic/nonstatic/native/
   abstract, absent method, duplicate exact method, malformed root-kind/config/args
   commitment, class declaration/binding/CAS and old/new selector confusion refuse.
   Include a valid overloaded main target. Keep actual error categories precise.
5. Demonstrate no host argv; null-vs-empty must be observably different. Wrong
   component type or null reference in a TEST-only corrupted copied fixture/state
   is a negative, never a permitted input API. No forced successful outcome.
6. Boundaries remain4/65536 and DI0 read4096; plus-one refuses in its actual layer.
   Per-publication failure/old-root retry and real terminal blob after void/exception,
   no engine install or repair CREATE on reopen. Full code pin and typed ABI checks.
7. Fresh20min4GiB sampled group watchdog; actual call gas/time <=100M30s, no1B.
   Source/patch/compiler/artifact/fixture/oracle/repro/refusal/strict-verifier evidence
   tracked; fresh ignored builds and scoped TMPDIR. Preserve all logs before cleanup.

At most two default-Terra/high workers; MR0 worker is sole semantic Solidity writer.
Parent owns independent reconstruction/replay and any later production freeze.
A working MR0 still does not solve target class capacity, density, required platform
APIs, lazy loading, or unchanged vanilla Minecraft startup.
