# Stock S2b-L parent integration / acceptance review

Accepted registration-only slice, frozen3fe8e0c; production fixes a6f9646. The latest
user priorities separately select local artistic MC1.12.2/Java8, relaxed finite
local gas and workload-specific platform support. This stock slice kept ALL its
original8M/standard-protocol gates; it is not a prerequisite for local MC work.

## Deliveries and independent findings
- Runtime dfb5e07 ->4ca0e94; harness d510d44 ->9d4ad62; verifier e5f2841 ->196d1e4.
  Harness worker session ended provider-flagged, despite a clean committed artifact.
  Parent inspected/integrated its commit and independently executed all harness
  tests; no worker final-success claim or partial unchecked test counted.
- Parent reproduced original preflight14classes/51calls and7936metadata at7864288gas.
- Parent independent raw order pair157B showed old prototype eligibility depended
  on declaration order: callerfirst domain0/cache1, badfirst caller Call4/cache0.
  Production immutable Phase-A envelopes fix it: both retain caller domain0/cache1,
  invalidcallee Bytecode11pc0; each registration398469gas.
- Parent JVM-valid271B raw/134Code CFG previously Bytecode14pc77. Production now
  eligible with exact128instruction starts,1458482registrationgas. Same bytes pass
  Java8/21 -Xverify:all for0/1/-1/MIN/MAX (ten JVMvectors). Independent verifier also
  tests legal192Code/279cumulativeenqueue graph. Neither is Java execution in S2b-L.
- Verifier exposed three malformed-analyzer replies accepted with methods33,
  literals257 orcalls33. Parent reproduced exact failures before fix, then bounded
  each incoming dimension before payload copy and in cached-header validation.
  Required S2bLinkError(2) now passes all three retained negatives. Known real
  analyzer already enforced aggregate caps; this was linker response hardening,
  not observed wrong metadata for the14normal classes.
- Parent moved bounded revert copying from scratch to free memory and added14
  lengths0/1/31/32/63/64/65/68/96/128/255/256/257/8097: exact passthrough for1..256,
  Link2 for0/>256, no partial metadata/nonce/event. No host-class parsing path added.

## Final artifacts and measured evidence
Pinned solc0.8.30 optimizer200/viaIR/Cancun/metadataoff; reproducible parent build.

| Component | init bytes | runtime bytes | runtime SHA256 |
|---|---:|---:|---|
| Analyzer |18568|18542|9ed5907864695906252b2fce0831d8e07ee6bc4fda6dfaef40d20617cd61181f|
| Linker |4966 (5062withargs)|4643 template|991af0ca7b71e4ff4f4a145992f5e286f51f494fb2b7055654c7e9f056c0602d|
| MetadataPage |339 (8595maxencoded)|3 constructor template|0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438|

Analyzer H6/EXTCODEHASH:
7dd80390b865891ff1c5f8fe9e067131231252dfd1a45939182c25a844133d45.
Issued metadata runtime is STOP||payload, not the3-byte compiler template. Actual
linker bytes/hash include3constructor immutables; verified against compilerrefs and
getters. Componentconfig hashes alone are commitments, not trusted-code attestation.

All14 exactclasses registered from rawEVMpages;51M3a callrecords(14+16+21), private/
overloaded/void/sixarg/recursive symbolic links, deferredbodyerrors and reusable
S2a-source reparse. Adapter anddirect samepage identity/idempotent realcounts.
No EVM execution of calls/recursion/faults/268catalogue. The268row/94root catalogue
remains TEST oracle evidence:261values,6ArithmeticExceptions,1profileSOE; Java8/21
and monolith checks agree,6702attemptedbytecodes/512dynamiccalls are oraclecounts.

Exact cap remains unchanged raw3574B SHA256
0e3e962a3de46d9c019c8e8e3e846b304622fc969144713f9ad6922c33946f33:
32methods/256literals/32calls,7936metadata payload. Direct7668234gas andadapter
7680072gas at actual8Mlimits, including metadataCREATE. Lowergas rollback/retry
retained. Final harness66signedtransactions/69986762totalgas across transactions,
NOT oneblock. Fourteen-class direct-registration sum17143256 andadapter sum17413952
are likewise many-transaction totals. Explicit signed replay verifies contexts,
roots/code/registry/events; walltime signedheaders are recorded, not fabricated.

## Parent gates
- make java-stock-s2bl-test java-stock-s2bl-demo: PASS, includes pinned buildcheck,
  all harness/verifier/parent tests. go vet ./jvmevm/stock/s2b:PASS.
- make java-test: artifact/24bootstraps/GoCLI/36Python/2231full allPASS.
- make java-smoke java-fast:1040/1060PASS; these tier names do not enable CodexFast.
- make java-demo java-aot-test:PASS.
- make java-stock-test java-stock-demo java-stock-s1-test java-stock-s1-demo
  java-stock-s2a-test java-stock-s2a-demo:PASS.
- Focused vet S2b/S2a/S1/S0/jvmevm/cmd/jvmevm:PASS.
- No oldfixture/outcome/budget/runtime or EVM/core/protocol changes. Monolith stays
 154839B SHA256 dfc81dbbea8253c644be2532a809a417bb40cd07eaca8ab5be72a84721eae929.

Logs /tmp/s2bl-parent-{initial-negative,integrated,production-probes,make-final}.log;
/tmp/s2bl-parent-legacy-gates.log and .exit=0. Original ignored parent generator/
reproducer under build/java-diff-stock-s2bl-parent/; production parent_test.go keeps
independent exactraw regressions and success-required assertions.

Next priority is the selected LOCAL MC path using richer monolith semantics:
bootstrap/String/Class/main dependencies plus explicit continuation/VFS/minimal
scheduler proposals. S2b frame execution remains unfrozen. No MC execution, EULA
acceptance, ready banner, JavaSE completion or durable-process-restart proof claimed.
