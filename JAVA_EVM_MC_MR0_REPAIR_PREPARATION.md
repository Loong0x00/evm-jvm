# MR0 measured-defect repair preparation

COPY-only, no accepted profile/source/ABI/quota change. Candidate MR0 remains
unaccepted. Transport d540fd6c3 supplies actual (not compiler-only) failures:
name-only overload selection MethodError2; legal args=null has q1 LC0StateError7
while q7 returns VOID. Parent will independently replay the originals and repair.

Authorize only these semantic changes in a NEW copied MR0 source/namespace artifact:

1. `_prepare` selects the unique exact name+descriptor main:([Ljava/lang/String;)V.
   Unrelated valid overloads do not count. Keep access/native/abstract/synchronized/
   Code and metadata validation. Duplicate exact matches still reject. If no exact
   target exists, report the documented missing-exact-method category, not an
   invented successful fallback; do not select ()V/(I)V/reference-return roots.
2. Empty non-null String[] is an INITIAL INPUT invariant, not a permanent local0
   invariant. Validate the canonical allocation immediately after installation and
   before any Java instruction. Remove only the overrestriction that revalidates
   current local0 as immutable input on each pending checkpoint. Java may rebind
   args to null or another array, or reuse its local. Keep ordinary frame/heap/ref/
   root-kind/empty-args/config/owner/package/anchor/opaque-checkpoint validation.
   Resume still uses only the successful EVM-issued checkpoint; it must not recreate
   initial args or read them from host state. Root kind/config and exact code bind
   the actual allocation history; do not weaken CAS or accept fabricated snapshots.

No Selected-table optimization/8-class/256KiB merge here. Keep4/65536,38 bootstraps,
CP4096/Code65535, existing heap/VFS/frames/fields/checkpoint,100M30s, no1B. Old engine/
coordinator artifacts and raw failures remain untouched. Build fresh copied MR0
engine/coordinator pins at isolated LOCAL initial-state route, no ordinary CREATE/
standard-chain/accepted identity claim for the oversized engine. Other controllers
and pages ordinary CREATE; all classes EVM AS0/ZI0/DI0 FINAL reads<=4096. No host
parser/catalogue/inflater/Java evaluator/raw class input/reflection/private-state/
page injection/failed-trace recovery. Separate Java8 oracles are generated TEST only.

Required repair controls: original positive overloaded main now reaches genuine
VOID; exact method among other overloads, <clinit>, input type/non-null/length and
retained array identity. args=null and args=new String[1] direct/q1/q7 all agree;
original argument retained separately by guest if identity is checked. Uncaught
Java exception remains typed outcome3 (including actual dynamic class identity),
not VOID or synthetic int0. Actual ABI component result is reserved zero; don't
pretend it is named differently or returned as Java int. No host argv surface.

Retain new-process/warm/memory/checkpoint/event/gas/root/counter/byte-read evidence;
negative descriptor/access/duplicate/old selector/CAS/config/binding/size cases and
publication-failure/retry as feasible, with exact failure layer and no result leaks.
Correct reproduction must REFUSE existing output—never run the old rm-rf wrapper.
Verifier must evaluate fresh outputs, not only archived expected receipts. Every
failure/log/watchdog is retained before cleanup. Fresh20min4GiB sampled group gate,
scoped TMPDIR, fully tracked source/patch/pins/fixtures/reproducers. Parent independent
rebuild/replay is still required before accepting even this generated preflight.
