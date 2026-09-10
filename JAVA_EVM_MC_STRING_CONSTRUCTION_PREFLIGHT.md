# MC String-construction dependency preflight

Status: **documentation and ignored measurement prototype only**, based on accepted
MC-LC0 at `8a65662`. This is not an implementation freeze or acceptance claim. It
does not authorize production/runtime edits, Minecraft execution, EULA acceptance,
VFS, `main`, builders, listeners, peers, core/consensus changes, or budget changes.

## Recommendation and ordering

The smallest useful slice is a new LOCAL **MC-SC0** runtime supporting exactly:

* public `String(char[])`, with a defensive UTF-16 copy;
* public `String(String)`, with a distinct String object sharing immutable backing
  and copying the hash cache; and
* the accepted eight native APIs, with `intern()` corrected for non-interned String
  receivers.

Keep `String()`, `String(char[],int,int)`, byte/charset constructors, substring,
concat, formatting, `StringBuilder`, `StringBuffer`, and all other String APIs hard
unsupported. In particular, Java 8 `StringBuilder.toString()` invokes
`String(char[],int,int)`: SC0 therefore does **not** claim builder support.

Preferred dependency order is: accept fresh-Throwable identity (M5d-b0) if that
single-writer slice is already next; then SC0; then a message/cause and
`StringIndexOutOfBoundsException` slice; only then consider the range constructor;
then freeze the VFS0 Java bridge. SC0 itself does not need fresh Throwable because
its honest ordinary failures are already-supported NPE6 and OOM7. VFS0 still needs
fresh `IOException`/`FileNotFoundException`/`EOFException` construction and message
semantics, so SC0 alone does not unblock VFS0.

Do **not** include the range constructor now. Java 8 and 21 probes agree that
negative offset/overflow raises `java.lang.StringIndexOutOfBoundsException`, while
a null array raises `NullPointerException`. Substituting existing
`IndexOutOfBoundsException`, a hard profile error, or a host check would be false.

## Bytecode/native boundary

Use a newly pinned bootstrap String class. Its two constructors are genuine trusted
Java 8 classfile Code and run through existing `new`, `invokespecial`, Object
constructor, fields, branches, `newarray`, `arraylength`, `caload`, `castore`, and
return machinery. The proposed `char[]` constructor uses a small bytecode loop
instead of Java 8 OpenJDK's `Arrays.copyOf`, because Arrays is not present; its
single-threaded observable result is the same defensive copy. `String(String)` uses
the Java 8 shape: share `value`, copy `hash`. Do not hard-code either constructor in
Solidity and do not add host String construction.

Native EVM service remains appropriate only for the existing eight exact reserved
String signatures. Seven keep accepted behavior. `intern()` must hash and compare
full UTF-16 content inside EVM: return the existing canonical object on a hit; on a
miss insert the receiver itself and return it. A full-pool hit still succeeds; a
full-pool miss raises Java OOM7 without mutation. Keep collision-safe full-content
comparison and canonical table ordering. No native constructor, Arrays emulation,
class-specific generated runtime, or host lookup is proposed.

Valid constructor descriptors receive ordinary exact method resolution and Code.
A syntactically valid unsupported String constructor remains
`StringProfileError(1,pc)`; malformed descriptors retain `CallError(4,pc)`
precedence. Null constructor arguments raise NPE6 at the guest `arraylength` or
`getfield`. Object/array/field/handle/pool exhaustion raises OOM7. EVM OOG, reserve,
checkpoint, and profile failures remain hard errors and never become Java outcomes.

## One authoritative heap and immutable backing

All constructed objects, source/copy char arrays, literal Strings, exceptions, and
intern entries use LC0's one `ExceptionArena.heap` handle namespace. There is no
second String heap. Generic allocation charges the String object and all inherited
instance fields first. `String(char[])` then charges one ordinary char array and all
its elements; `String(String)` charges no array and may share only an existing
String backing. Existing limits remain: 1024 ordinary objects, 1024 arrays, 65,536
array length, 262,144 elements, 65,536 ordinary field slots, 1024 fields/object,
1024 intern entries, and the existing handle/checkpoint bounds.

The source char array is never installed as `value`. During the constructor loop,
the fresh destination is reachable only from the constructor frame; after return,
only String `value` fields may retain it. Multiple Strings may retain one backing
only through `String(String)` or canonical intern identity. Validation should reject
an initialized String backing also reachable through an ordinary array/static/
object/local reference; while its constructor is active, permit the exact temporary
frame alias. Private-field access rules and absence of reflection are not a
substitute for checkpoint validation.

Inherited Object fields remain base-first, defaulted, typed, and charged exactly as
accepted LB0. Locate String's own `value:[C` and `hash:I` by EVM-parsed declaration,
not fixed offsets or an assumption that String has exactly two total fields. The
accepted Object0/1/1022/1023 String layout/OOM regressions must remain.

## Construction failure and LC0 yields

Allocation is intentionally not one atomic Java operation. `new String` publishes
an uninitialized ordinary object before `invokespecial`. A yield may therefore
contain that object with null `value`; the char constructor may later contain its
fresh partially copied array in locals. Constructor return promotes aliases only by
the accepted constructor rules. No opcode/allocation/copy iteration repeats on
resume.

If the argument is null, or backing allocation raises Java OOM, unwind removes the
usable uninitialized reference but no-GC accounting retains the now-unreachable
failed String object. Do not refund its object/field quota. A backing-allocation
failure may retain the default String but no half-published backing. EVM OOG reverts
the whole slice to the old anchored checkpoint instead.

LC0's decoder currently rebuilds String layout only when `internCount != 0`, and
then requires **every** allocated String to appear exactly once in that table. Both
assumptions must change in a new schema: rebuild layout whenever any String object,
String frame, or intern entry exists; intern entries must still be valid, unique,
content-distinct, hash-correct, and ordered, but non-intern Strings are legal.

For deep validation, require every reachable initialized String to have a valid
rank-1 char backing and hash field equal to zero or the content hash. An active
String constructor may have default fields or its exact in-progress backing state.
An unreachable failed residue may be accepted only with exact default fields;
unreachable completed Strings remain structurally valid. Recompute reachability in
EVM from frames, statics, objects, arrays, and pending state. Live resume still
requires exact owner/epoch/head/runtime/artifact/config commitments; standalone
semantic validation is not provenance.

## Versioning and preservation

Do not edit or relabel accepted artifacts. LB0 remains 166,385 bytes,
`ea94075540b8b66aa8e85823ee66e9dba4a2be65f29942855a8f59478bca0cbf`;
LC0 remains 206,163 bytes,
`a1820864d8e846be4de8211158778150fdfde0e41e443aa66c44ec17f487e6cd`.
All accepted 24/27 bootstrap bytes remain byte-identical in those targets.

SC0 should be a separately named runtime/contract with a new bootstrap root,
config domain, machine magic/schema, artifact, and Go package. It may derive code
from LC0 but must not reinterpret, upgrade, import, or resume an LC0 schema-1 blob.
Existing LC0 instances continue only on the accepted LC0 contract. SC0 starts fresh
instances; no host state migration API is proposed. One Solidity writer owns any
later frozen runtime.

## Candidate acceptance tests

1. Java 8, Java 21, one-call EVM, q1, and q7 agree for empty/ASCII/NUL/surrogate
   arrays, defensive source mutation, distinct copy identity/equality/hash, null,
   and intern hit/miss/first-wins/collisions.
2. EVM checkpoint inspection proves distinct source/backing handles, String(String)
   backing sharing, literal-versus-copy identity, and no host-created handles.
3. Stop before/after String allocation, Object return, backing allocation, loop
   iterations, final `putfield`, constructor return, pending NPE/OOM, handler entry,
   and intern insertion. Resume never repeats a completed effect.
4. Catch null and exact/plus-one object, inherited-field, array, element, handle,
   checkpoint, and intern-pool limits. Failed operations preserve prior objects,
   pool entries, counters, head, and logs according to Java versus hard-failure type.
5. Mutate/re-hash TEST checkpoints for non-intern value/hash/backing type/rank,
   exposed backing aliases, active constructor locals/PC, failed residues, duplicate
   intern content, and table order. Standalone validation rejects exact bad states;
   every host-changed state also fails live-head binding.
6. Unsupported/range/wrong descriptors, user String replacement/lookalikes, private
   field access, native flags/Code precedence, and wrong receiver kinds preserve
   exact error precedence. No fallback consults host JDK Strings.
7. Exact accepted LC0 chains/durability and all LB0/2231/stock/bootstrap/artifact/
   CLI/Python/demo/AOT gates pass unchanged. Report SC0 counts separately.

Retain LOCAL 100,000,000 gas/30 s per ordinary call, 1,000,000,000 gas/120 s only
for dedicated boundaries, 25M commit reserve, 1 MiB checkpoint, and LC0 per-call
1..4096 JVM/internal units. Gate processes use an external 20 min/4 GiB RSS
watchdog and at most 256 slices/case. Maximum-length constructor completion is not
guaranteed within 256 test slices; do not lower accepted array quotas or claim
liveness. No historical budget changes.

## Ignored prototype evidence

The ignored prototype changed only `build/java-diff-mc-string-construction-preflight/`.
Its bootstrap String is 984 bytes, SHA-256
`7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad`;
`SCProbe.class` is 1,116 bytes, SHA-256
`653e1b8b580922cd8a93212ed4c06d42d8f11a6ff85760c197e2233a49d4ef06`.
The 207,145-byte solc 0.8.30 runtime SHA-256 is
`01e2c9ce16f50bfba925e6d53acdef9777a52b316c17e7c2b01a53060cb82864`.
This oversized, minimally patched runtime is measurement evidence, not production.
Its pool-full path deliberately remains a hard prototype error, so it is not an
acceptance candidate.

Java 8/21 both returned defensive=97099, literal-copy-intern=111,
constructed-first-intern=111, null-then-valid=12, and loop64=64076. EVM matched.
Selected linked-chain measurements (gas is summed across calls):

| case | q | slices / JVM units | total gas / max call | final bytes |
|---|---:|---:|---:|---:|
| defensive | 4096 / 7 / 1 | 1/87; 13/87; 87/87 | 5,513,986; 50,323,953; 324,022,796 / 5,513,986 max | 733 |
| first constructed intern | 4096 / 1 | 1/198; 198/198 | 6,767,921; 808,276,752 / 6,767,921 max | 1,031 |
| null then valid | 4096 / 1 | 1/73; 73/73 | 5,454,417; 297,282,855 / 5,454,417 max | 871 |
| loop64 | 4096 / 7 | 1/1711; 245/1711 | 12,294,113; 949,199,567 / 12,294,113 max | 1,708 |

All compared quantum choices produced the same final machine root per case.
Checkpoint inspection found defensive String handle 3 default-valued through its
active constructor, copy-array handle 4, then `value=REF(4)` before constructor
return. Null construction retained failed default String handle 2, NPE handle 3,
and later completed String handle 4/backing 6. This directly confirms the codec and
no-GC residue issues above.

Actual commands were `javac --release 8 -g:none`, Java 8u504 and Java 21.0.9 oracle
runs, pinned npm solc build, `timeout 1200s go run
./build/java-diff-mc-string-construction-preflight/run_probe.go`, and the read-only
`inspect_checkpoints.py`. `evm-measurements.log` SHA-256 is
`f84b66f09b42f12e66a5b0413443d7cbcbd3eab6cb554fb08492545726f2540b`;
inspection log SHA-256 is
`46416f03f4af64a6e6579a6f8d69f0467df2c287a5ec4e42414d5e93433326e3`.
No RSS high-water measurement was made.

## Unknowns before a freeze

Exact production code size/gas after honest OOM routing and full validator work is
unknown. Maximum practical copy length under checkpoint/slice limits is unmeasured.
Pool insertion ordering, every malformed-state precedence, inherited-layout
boundaries, OOG rollback, durable new-process reopen, and all old gates were not
prototype-tested. Throwable/message and range-constructor bootstraps remain
unfrozen. Dynamic Minecraft reachability and required path/builder constructors are
still unknown; no Minecraft artifact was read or executed here.
