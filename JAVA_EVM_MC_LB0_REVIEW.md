# MC-LB0 parent integration review

Status: **parent integration/regression gates PASS; extra independent review still
pending**. Not yet the final LB0 acceptance checkpoint. Frozen920798f and latest
JAVA_EVM_PROGRAM.md apply. This is LOCAL String-core evidence, not MC startup,
standard deployment, full String/JRE support or continuation.

## Integrated deliveries
Runtime318def6 ->74b718c; harnessa69feab ->60ed095; verifier47b1234 ->010f199.
Parent fix f50fe14. Initial166311B artifact2a54eca7... passed the64catalogue and
verifier, but parent independently found a remaining inherited-layout quota bug.

A supplied TEST Object with1022fields gives String1024inherited+own fields and
must allocate. Object1023 gives String1025fields and must raise ordinaryJavaOOM7.
The initial candidate instead hard-reverted BootstrapProfileError(1,0). Parent
changed layout preparation to report allocation failure without constructing an
over-limit defaults array; ordinary exception routing/catch now works. Exactcase
retained, including a subsequent ordinaryObject allocation and anotherStringmiss.
A separate failedString ConstantValue preparation correctly marks its owner
erroneous and produces subsequentNCDFE12, result19, gas17990430.

Final candidate runtime: **166334bytes**,
SHA256 **ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982**.
Pinned solc0.8.30/optimizer200/viaIR/Cancun/metadataoff reproduces it. All24old
bootstrap source/hex images are byte-identical; three new profiles total27:
Comparable196B,CharSequence216B,String787B, hashes frozen in LB0plan/build.js.
No Go production parser/transcoder/runtime fallback, core/opcode/gas-accounting/
precompile/consensus changes. Oversized local runtime.Execute still bypasses
standarddeployment setup; no standardCREATE/transactiongas claim.

## Parent probes / finite evidence
- Exactly64newcatalogue rows (62ordinary,2boundary) pass independently on Java8,
  Java21 and EVM, with the same trusted rawclassbytes and integer-root ABI.
  Nineclassimages/eleven sourceinputs; catalogueSHA256
  55b1634732096151efb5a1c4df33ac37b7f4eee3a6075b5220d0b8a51e2a63e9.
  Fixture regeneration yields no diff. No javac-folded method/field substitution.
- Parent192seeded UTF16 vectors over96literals pass Java8/21/EVM; includes MUTF8
  boundaries, paired/unpairedsurrogates, hashes/compare/equality, interfaces/bridge,
  intern/arrayaliases and caughtNPE/CCE. GeneratedclassSHA256
  22c6c6ba84743804e4b4963caaf00b26865151cb625979010440a1c7d2cfc349;
  maximum16241324gas, wholewatchdog30s, everyEVMcall<=100M.
- Four inheritedlayout probes: Object0/1/1022/1023, firstthree value1 and last7.
  Exact1024Stringfields uses18048491gas; oversized1025fields caught/retry20,142,510.
- Inherited preparation poison case above, and aggregatequota case:65410ordinary
  fields already allocated, next1024-field StringmissOOM, existingStringinternhit/
  hash/charAt remain intact; value8 at72260965gas. These six layout/quota cases
  are explicit EVMprofile tests, NOT a hostJVM with replacement java.lang.Object.
  TotalparentEVM probes198; only the192semanticvectors have JVMparity claims.

Final candidate dedicated verifier measurements (all<=frozen1B/120s):

| Boundary | gas |
|---|---:|
| fullpool hit/failedmiss/collisions |540235533|
| ordinaryobject quota |204847973|
| dormantroot preparationOOM |162452319|
| arrayelement quota |159445060|
| longcommonprefix |141128945|
| dependentpreparation poison |123354557|
| max65535-byte MUTF8 |106745890|
| ordinaryfield quota with String |87107988|
| ordinaryarray count |32595985|

No old budget was increased. Stringboundaries use NEW explicitly frozenLOCAL1B;
ordinarynewcases100M. Internpool hashes use Java32-bit Stringhash with fullcontent
comparison, so actualcollision cases are reproducible, not assumed keccak collisions.
Per-invocation Stringobjects/chararrays/pool use the same authoritative handle heap
and counters as ordinaryallocations/exceptions. No host-created Java state.

## Regression and oracle-pin review
Parent `/tmp/mc-lb0-parent-final-gates.exit` is0:
- make java-test:27bootstrap/artifact/GoCLI/36Python/2231full PASS.
- make java-smoke java-fast:1040/1060PASS (tiernames not CodexFast).
- make java-demo java-aot-test:PASS.
- make java-mc-lb0-test java-mc-lb0-demo:PASS.
- stockS0/S1/S2a/S2b-L tests/demos/artifactchecks allPASS.
- focusedvet jvmevm/cmdjvmevm/allstockpackages:PASS.
- Additional aggregateparentprobe+vet after the fullscript:PASS; no runtimechange.

The first pre-fix fullrun passed2231/smoke/fast/GoCLI/Python but stopped at S1's
hardcoded historical monolith TEST-oracle hash. Parent explicitly preserved that
old dfc81dbb... pin and added ONLY reviewedcurrentff9c9ff0... to S1/S2a oracle
allowlists. Independently reran unchanged82/201catalogue comparisons successfully
before fullregression. Stock executable artifacts, inputbytes, outcomes and budgets
were not changed. Go monolith expectedRuntimeHash now pins currentff9c9ff0... .
No obsolete tag8negative was found or deleted; Classliteral remainsBytecode13.
Old24bootstrap comparison and upstreamcore/protocol diff are clean.

Logs: /tmp/mc-lb0-parent-{build,integrated,inherited-initial,inherited-fixed,probes,
aggregate,stock-oracles,final-boundaries,fixtures,final-gates}.log. Original failed
initialstockpin run is /tmp/mc-lb0-parent-legacy-gates.log/.exit=2, not a passing
acceptance log. `mc_lb0_parent_test.go` keeps generatedseed/rawlayout reproducers.

## Remaining boundary
Extra independentStringreview at /home/user/evm-jvm/mc-lb0-independent-review is
pending. LC0 actual-engine checkpoint feasibility preflight is separately active
at /home/user/evm-jvm/mc-lc0-preflight; no productioncontinuation freeze yet.
charAt outsidevalidindex and deferredString/new/format/etc APIs remain hardprofile
errors. Root still(I...)I, no main/Stringconstruction/Class/VFS/thread/scheduler/
logger or MC execution. No EULA acceptance or realDone output.
