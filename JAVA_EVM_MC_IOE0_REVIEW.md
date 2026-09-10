# MC-IOE0 acceptance review

Status: **ACCEPTED bounded LOCAL exception message/cause library**, after parent
integration and independent gates through `a6238f5`. Authority is frozen
`JAVA_EVM_MC_IOE0_PLAN.md` (`0534a7f`). This is not a file bridge, VFS, logging,
stack-trace implementation, standard deployment or Minecraft startup claim.

## Artifact and scope

Worker59b7525/bc0288b integrated asbc0127f/0fe4038. Parent added the independent
32-group gate at e6ec570 and supplementary checks at a6238f5. Actual integration,
not temporary worker overlays, established the evidence below. No production runtime
correction was required by this parent's checks in this stage.

* Contract `jvmevm/runtime/local/ioe0/IOException0Interpreter.sol`.
* Runtime233286bytes, SHA256
  `507ed54d56d4cbe5e559013fbf5a3e598d75a28c0ffe33735573f646eac659a0`.
* Source SHA256
  `de0a45a5911f5e792aa69f776096a78afaf11e246b7b53d5cf67f9b7a1df7086`.
* Runtime Keccak/code hash
  `8803cee137ce7cc78ee66798e4c82d6ae7ae44626010cd3353f1c8aeb04ad940`.
* Exact solc0.8.30+commit73712a01, optimizer200/viaIR/Cancun/metadataoff;
  separate runtime/ABI/embedded combined source/bootstrap provenance reproduce.
*30 images:24 unchanged SC0 images, three versioned substitutions (Throwable,
  Exception,EIIE), three appended I/O images. Parent independently recompiled all
  six new images with Java8 and compared every byte; String remains984B unchanged.
* Accepted SC0/TL0/LC0/LB0/stock files and old images stay untouched. No upstream
  EVM/state/types/consensus/protocol change or production host Java evaluation.

Constructor/getter Java Code now supports the frozen Throwable/Exception message
surface, IOException/FNFE/EOF zero/message constructors, and EIIE exception/cause
getters. Message identity is preserved, not copied or fabricated. EIIE's actual
field is the sole cause authority; the old side table is absent from IES1.

VM exceptions initialize canonical cause=self and message=null in the existing
arena. There is NO new VM-message String, carrier method, message quota or handle
extension. VM AE getMessage and other unmodeled VM getter cases hard-fail with the
frozen ThrowableAPIProfileError instead of returning a fake value. Ordinary no-arg
AE remains distinguishable from VM AE. Supported getters execute actual Java Code.

Null/self constructor transients and already-legal escaped REF aliases remain
admissible. Ordinary EIIE may reference a later-allocated cause or Error; VM EIIE
requires its prior non-Error cause. Wrapper allocation failure stays emergency OOM,
without a fictitious EIIE field. String's SC0 Object profile remains String-new-only.
Unsynchronized getter image pins claim single-stack value semantics, not monitor or
thread equivalence. initCause and other deferred APIs remain unsupported.

## Actual verification

*24 Java8/EVM roots agree (23 return1, failedClassLater returns3), with24 real
 one-call controls and ten q1/q7 selections (**20 linked chains**). Terminal roots,
 counters and message/cause references agree across IOE0 quantum choices.
*Java21 is secondary:21 roots agree, while implicitNPE, wrappedNPE and
 constructorFailureAfterSuper return0 because helpful NPE messages are nonnull.
 These exact secondary observations are explicitly checked; Java8/EVM expected
 outcomes are not rewritten and Java21 helpful messages are not disabled.
*Highest core one-call cost13767080gas; largest core terminal checkpoint1275bytes.
 These are small fixture measurements, not a Minecraft startup estimate.
*Legacy SC0/TL0/LC0 outcome controls remain valid on IOE0. New Throwable constructor
 stores legitimately add JVM opcodes: cross-profile counters are NOT forced equal.
*All32 parent-owned independent groups execute against the actual artifact, not
 stubs. They cover image/profile/access/getter origin, quotas and inherited fields,
 canonical messages/self/cause/chronology/cycles, constructor phases, namespace/CAS,
 OOG/reserve/publication failure, and genuine new-process mid-constructor/wrapper
 reopening without code reinstallation.
*Supplementary parent tests prove interface getters use ordinary dispatch/Code and
 a VM EIIE with1026 physical fields remains legal under the arena quota. Its1025-field
 implicit cause plus1025-field emergency OOM account for3076 arena field slots;
 ordinary per-object1024 limits were not improperly applied to arena objects.
*Exact1MiB and plus-one new-profile checkpoints, full ordinary heap with available
 VM AE,256 implicit exceptions/emergency OOM, wrapper OOM, and synthetic Object
 throwing this before Throwable's cause store pass. The synthetic Object case is
 EVM-profile evidence, not a modified host-JDK oracle.

Initial parent test corrections were confined to tests: recalibrating the new
exact-size fixture, expressing the checked IOException catch through a declaring
helper, and correcting the serialized counter offset. They were retained/retested;
no guest outcomes or production semantics were weakened.

## Records and resource limits

* `/tmp/mc-ioe0-parent-gates.exit=0`: newIOE0 plus all historical SC0/TL0/LC0/LB0,
 2231/full/smoke/fast/bootstrap/Python/artifacts/Go/CLI/stock/demos/AOT/focusedvet.
* `/tmp/mc-ioe0-parent-final-tests.log`: complete final package after all parent
 supplemental tests passes in39.627s; focused IOE0/runtime-assets vet passes.
* `/tmp/mc-ioe0-parent-watchdog.{log,json}`: harness plus32-group run under external
 1200s/4GiB process-group watchdog passed in38.82s, peak observed RSS296017920bytes.
 The two later supplementary tests also passed in the complete final run above.
 Measurements are machine-specific, not universal performance bounds.
* `/tmp/mc-ioe0-parent-reproducibility.log`: exact final artifact reproduction;
 parent rebuilt fixtures in an ignored copy and compared class/manifest bytes.
* `/tmp/mc-ioe0-parent-corpus.log`, `parent-32.log`, `parent-additional.log` and
 `parent-counter-bounds.log` retain actual EVM evidence. Tests live in repository
 validation_test.go/parent_test.go and no missing-artifact skip is acceptance.

Runtime<=256KiB,1MiB checkpoint,100M/30s ordinary,1B/120s boundaries and25M reserve
remain unchanged. Dedicated quota tests use the frozen65536-total-unit allowance.
LOCAL code installation/runtime.Call is not CREATE or signed-transaction proof.
Opaque host checkpoint/trie persistence is not guest filesystem behavior; physical
power-loss or isolation from concurrent external filesystem replacement is not claimed.

Exactly two implementation agents were used; parent independently wrote/ran the
verification gate and made the acceptance decision. No Minecraft server/EULA/listener
or genuine Done occurred. `JAVA_EVM_MC_VFS0A_PREFLIGHT.md` is the next proposal only;
its filesystem code and gas/checkpoint costs remain unimplemented/unmeasured.
