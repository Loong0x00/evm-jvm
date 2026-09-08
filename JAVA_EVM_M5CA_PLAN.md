# M5c-a: variable-width control flow and wide locals

Authority JAVA_EVM_PROGRAM.md; last-green M5b-b862a56a:1593 oracle cases plus48
probes,36 Python,732 smoke/752 fast and focused gates. Runtime111218 bytes SHA
ad3aeff4e658741374e76cf2bb76d33e392929f640feca563255fa7f89631dac.
All NEW agents Sol/high WITHOUT Fast/priority; never --fast or enable preference.
Named make java-fast is allowed fixture tier, not agent speed. Continue bounded
implementation/independent verification automatically, no routine confirmation.

## Scope/invariant
Add tableswitch0xaa, lookupswitch0xab, goto_w0xc8, wide0xc4 for existing supported
local operations. All parsing/predecode/branch lookup/local/guest execution remains
INSIDE ordinary EVM bytecode. Host only supplies unchanged raw classes/int root
args, invokes EVM and decodes. No host parser/translator/evaluator/heap/AOT/native
precompile/JRE fallback/consensus changes. Trusted javac/JVM only build/oracle.
Local runtime.Execute, not deployed/full JVM. Preserve1593 fixture entries/sources/
outcomes/budgets, exact(I...)I root ABI, all numeric/reference/heap/init/call semantics,
limits and three bootstraps. No new JavaException kinds (1..11/schema1 unchanged).

IEEE values/arrays, jsr/jsr_w/ret/returnAddress, handlers/monitors and new Object/JRE
APIs remain deferred. No string/enum-switch library support implied; int computational
switches only. Existing max Code65535, stack/local1024 JVM words, frames128 and heap
quotas unchanged. Wide u16 indices do not increase the max_locals limit.

## Shared bounded predecoder
Refactor static-width-only assumptions carefully. Two passes still decode ENTIRE
selected Code, marking actual instruction starts, then validate ALL branch/switch
edges (including unused case/default targets). Only prefix0xc4 starts a wide
instruction; its embedded opcode/index/immediate are operands, NOT branch targets.
Switch padding/headers/pairs/offsets also aren't instruction starts. Preserve every
existing opcode's width/type/return/CP/branch validation and per-method caching.

Use widened mathematical/signed arithmetic for sizes/displacements. Bounds-check
remaining Code BEFORE payload reads, multiplication, allocation or loops. Malicious
high-low/npairs must not allocate huge EVM arrays, overflow or become generic panic.
Truncated instruction/header/table/padding -> existing BytecodeError2(opPC).
Invalid branch (negative, >=Code length, non-start) -> BytecodeError12(opPC).
New BytecodeError15(opPC): malformed variable-width STRUCTURE (low>high, negative
npairs, unordered/duplicate lookup keys, invalid wide embedded opcode). Unsupported
but recognized wide fload/dload/fstore/dstore/ret forms -> BytecodeError6(prefixPC),
not fake float/return-address support. Invalid other opcodes remain Bytecode6.
Keep unsupported return descriptors/CP/atype and existing error precedence; isolate
multi-fault tests rather than claiming complete classfile dataflow verification.

## tableswitch / lookupswitch
For opcode at METHOD-CODE-relative PC p:
  pad=(4-((p+1)%4))%4; header=p+1+pad.
Alignment is relative to code[0], NOT classfile/EVM-memory offset. Padding byte
VALUES are unrestricted in JVMS SE8: accept nonzero padding. Do not add a zero-byte
requirement (parent checked the official SE8 instruction spec).

tableswitch: big-endian signed32 default,low,high then(high-low+1) signed32 offsets.
low<=high; size12+4*count after padding, count computed wide and bounded by remaining
Code. Key is computational signed int32; consume exactly one INT value, preserve
prefix. If low<=key<=high choose indexed entry; otherwise default. Range extremes
MIN_INT/MAX_INT and negative keys are signed, not unsigned.

lookupswitch: big-endian signed32 default,npairs then npairs(match,offset) pairs.
npairs>=0, zero pairs valid. Match keys strictly increasing signed int32, duplicates
invalid. Size8+8*npairs bounded before loop. Key exact match selects offset, else
default. Bounded linear or binary search allowed, but no host specialization.

Every default/case offset is signed32 relative to OPCODE p, NOT aligned header or
instruction end. Duplicate TARGETS are valid (duplicate lookup KEYS are not).
Fall-through from one case's normal code is ordinary sequential bytecode. Validate
all table edges even if only one key is executed. Wrong key ref/null/long/uninitialized
kind -> Bytecode14, absent key Bytecode3. All I/Z/B/C/S computational ints work;
no implicit local narrowing, no long switch key.

## goto_w
Width5 with signed32 big-endian offset relative to opcode PC. No stack effect.
Preserve prefixes/int/ref/long values and initialization/frame state. Backward/self
branches valid if target is instruction start; finite gas still bounds loops.
Offsets beyond +/-32767 must not truncate to16 bits. Do not enable jsr_w0xc9.

## wide
Supported embedded ops: iload15,lload16,aload19,istore36,lstore37,astore3a,iinc84.
Load/store total width4: prefix,embedded opcode,u2 UNSIGNED local index.
iinc total width6 adds SIGNED16 increment. Apply existing typed local/initialized/
uninitialized-ref/category2 semantics, not parallel weakened helpers. Long locals
may begin odd; require n and n+1 within actual max_locals, preserve overlap
invalidation on ALL stores. Invalid local range Bytecode8; invalidated/uninitialized
Bytecode11; type/tail misuse Bytecode14. iinc operates computational int modulo2^32
with signed16 delta (-32768..32767), not unsigned and not field-like subtype narrowing.

The embedded opcode may never be targeted independently; branch to wide prefix
is allowed. Unsupported F/D/ret wide forms stay Bytecode6 at prefix; malformed
nested wide/arithmetic/other non-wideable embedded opcode Bytecode15. Do not read
past Code while selecting width. Root/predecode/call/return word bounds unchanged.

## Evidence and coverage
Parent verified SE8 6.5 tableswitch/lookupswitch/wide/goto_w and 4.9.1 constraints:
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-6.html
https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html
Use bounded trusted Java8 probes for nonzero padding and valid raw long-distance/
wide/local/category forms; malformed structural probes are interpreter validation,
not claims that invalid classes pass HotSpot verification.

Append~60-90 trusted Java8 m5ca cases, preserving1593. Dense/sparse/negative/extreme
keys, default/zero-pair via raw Go fixture if javac won't emit, fall-through, nested
switch/loops, calls/default/interface/initialization switch bodies, long/ref operand
prefix handling where valid, wide I/J/ref locals and signed16 iinc, forward/backward
goto_w. Force genuine javac wide with bounded generated >255 live locals and large
increments, and genuine goto_w via a selected method >32767 but <=65535 bytes;
inspect Code/CP/MAX_LOCALS and budgets. Large static generated fixture source is
okay, no host runtime code specialization. Avoid enum/String/JRE/F/D/jsr/handlers.
Fresh bounded JVM oracle sizes/timeouts, no memory exhaustion.

Independent Go: all4 switch alignments and nonzero padding, signed counts/keys/
offsets, header/table truncation, negative/huge npairs and overflow-safe high-low,
unsorted/duplicate keys, invalid default AND untaken targets, jumps into padding/
payload/wide embedded opcode, goto_w signed boundaries/backward/OOG loop, wide
u16 index255/256/1023 and long1022/1023 bounds, odd/overlap/tail/initialized checks,
signed iinc -32768/32767 and int overflow, unsupported/invalid wide forms and exact
prefix PC errors, switch key kind/prefix/call/init effects. Derive PCs via actual
instruction decoding, never scan arbitrary table payload as opcodes. Quotas and
outcomes1..11/OOG distinction unchanged.

Old blanket switch/wide negatives may be obsolete: report exact cases/new supported
or structural behavior; parent explicitly updates while preserving unsupported
IEEE/jsr/ret and genuine malformed/access/type guards. No assertion weakening or
old fixture/budget changes. Demo sum100 currently2986502gas against3M: report
measured regression if any, don't silently raise budget.

Parent integrates runtime->fixtures->verifier; independently checks pinned artifact/
3bootstraps, Go/CLI/Python1593+fulloracle/smoke/fast/demos/AOT/vet plus probes, accepts
last-green and freezes bounded IEEE representation/conversions/arithmetic next.
Raw-bit observability contract for IEEE is a FUTURE decision, no host/JRE shortcut
or intrinsic implemented here. No routine confirmation/full-JVM/deployment claim.

## Ownership
Runtime ONLY Solidity/runtimehex;jvmevm/jvmevm_test.go HASH ONLY;
new jvmevm/variable_controlflow_test.go runtimeM5ca* helpers. No host/API/decoder/
CLI/bootstrap/build/compiler/harness/fixtures/other old-test edits; report obsolete
guards. Fixtures ONLY differential/** stage m5ca preserve1593/schema1; baseline
stage rejection -> bounded manual trusted oracles, no harness edits/fake EVM-green.
Verifier ONLY tools/java_diff.py,tools/test_java_diff.py,tools/JAVA_DIFF.md,
new jvmevm/variable_controlflow_validation_test.go verifyM5ca* helpers; baseline
red expected. Parent owns plans/AGENTS/quickstart/Makefile/integration/profile updates.
One Solidity writer, no spawning/peer writes/push/global config/untrusted Java.
All agents Sol/high WITHOUT Fast; scoped commits and honest SHA/size/checks/errors.

## Accepted integration evidence
Runtimea4bf175→caf2f8b,fixtures461a3c1→c63d08e,verifier5021d8f→c5bf48a.
Review96f1813→115e683 fixed y initialization and included nested Box; JVM-verified
expectations preserved. Generic second-pass start-map traversal avoids width
redecoding; common iinc moved to dispatch front with one instruction per iteration.
Large forward taken119101982→68530373 gas, backward twice166313134→88410696;
all fixtures/input/100M budgets unchanged. No AOT/coalescing/skipped guest work.
Nonzero padding proved with ONLY padding mutated in original major52 Code and
StackMapTable, Java8/21 accepted; prior major49 oracle rewriting explained the
legacy verifier discrepancy. No incorrect EVM-only-as-JVM claim retained.
Parent final artifact/3bootstraps, Go/CLI,36 Python,1681 full,773 smoke,793 fast,
demos,AOT,focused vet and48 independent probes passed:
`build/java-diff-parent-m5ca/probe-prcg3zbf/results-final/`.
Prior1593 fixtures/budgets unchanged. Runtime116023 bytes SHA256
`1ea50d09775eb2422f618d4bb0fd0b1d7b867083c19a48c2e0b84f7390e2753d`.
Next explicit pure-EVM IEEE raw-bit service/representation/conversion contract;
no host math/native precompile permitted. All agents NO Fast.
