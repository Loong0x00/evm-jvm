# P50 parent-verified default ArrayList construction

Parent independently reproduced the exact old int-constructor image and current Java8 image, rebuilt engine/coordinator/driver, ran fresh q1/q7/raw150/coarse/private-state/refusal/new-process-reopen gates, and a fresh original125 package. No parent guest-semantic correction was necessary. All114 ordered roots and actual source DBOOT match the candidate.

Independent same-input int-only comparison proves real new class-initialization cost: P49 56J/3 arrays -> P50 60J/4 arrays, no quota increase or skipped initialization. Default instances share a genuine empty sentinel; int(0) retains its distinct real array. No add/growth behavior is admitted.

See `../parent-array-list-default/` and root `JAVA_EVM_MC_ARRAY_LIST_DEFAULT_PARENT_PREFLIGHT.md` for parent acceptance. Historical worker results below retain their provenance.

---

## Historical worker report

# P50 bounded ArrayList default-constructor candidate

Source-only candidate based on accepted P49 `451c7619135e8d38d87ed74fbadba650603f9b6a`.
It replaces only ordered bootstrap leaf 98 (`java/util/ArrayList`), keeps all 114
bootstrap positions and all other 113 ordered image commitments byte-identical,
and adds no class image, ABI, native binding, heap accessor, codec or limit.

`ArrayList()` is ordinary Java 8 bytecode: it invokes the real `AbstractList`
super-constructor then assigns `elementData` from a private static final
zero-length `Object[]`. Ordinary guest `<clinit>` creates the shared sentinel.
The unchanged int constructor keeps its negative-capacity `IllegalArgumentException`
and eager `new Object[initialCapacity]` behavior; it uses a distinct array for
`new ArrayList(0)`. `size` remains JVM-default zero. No ten-element allocation,
`add`, growth, `get`, iterator, clone, typed-array, equality or hash behavior is
implemented. Those method attempts are checked as atomic raw refusals.

The class is compiled with `/usr/lib/jvm/java-8-openjdk/bin/javac -source 8
-target 8 -g:none`; `compiler-support` contains compile-only minimal interface
symbols for the already-present bounded Java utility images. These stubs are not
included in the runtime or raw Java bundle. Fixture sources are host-Java-8
oracle/build inputs only; the generated fixture bytecode is executed only by the
EVM harness, never by host Java. The only archive inputs are synthetic ZIPs made
from these fixtures; no original Minecraft JAR, classes, resources, worlds or
receipts are used.

## Reproduction and result

From the repository root, run `build-candidate.sh`, then
`test-fixtures/build-fixtures.sh`, then `run-gates.sh <new-unique-run-id>`.
These scripts use pinned offline solc 0.8.30, the local Node dependency path, and
Go with `GOPROXY=off GOSUMDB=off`. All logs/reports are outside a world's strict
store directory. Run directories are append-only; use a fresh ID.

`pins.json` and `bootstrap-root.json` record the actual deployed-bytecode lengths
and hashes and root derived from the engine's literal `JVMEVM:...:BOOTSTRAP:1`
source domain. `runs/candidate-gates-006-verification-report.json` records fresh q1/q7/q128
completion and reopen, equal machine/VFS roots, int-negative guest exception catch,
seven unsupported-method refusals, raw bootstrap replacement refusal, and classfile
sentinel/int-constructor structure. An int-only fresh guest main (only `ArrayList(0)`
and `ArrayList(3)`) completes 84 q1 JVM steps while triggering ordinary class
initialization; its whole-world EVM gas is 3,157,378,007, maximum individual call
39,464,487 gas and 54 ms (the total includes setup/transport, not a claimed isolated
clinit-only charge). Each raw refusal confirms unchanged EVM root and durable Head.
Earlier gate runs 001 through 005 are preserved (including harness failures); run
006 is the completed gate for the final artifact pins.

This is a worker candidate, not parent independent acceptance. It does not claim
ArrayList mutation/expansion or Minecraft execution.
