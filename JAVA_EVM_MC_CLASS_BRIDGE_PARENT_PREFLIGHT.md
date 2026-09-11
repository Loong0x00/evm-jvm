# Class bridge parent replay and input-size finding

Status: **preflight only, NOT a production bridge/ClassLoader acceptance**.
Worker e3f45ec22 integrated5ce5ffe37, no accepted production changes. Parent reran
tracked run.sh into a fresh ignored workspace. Exact original disposable artifact
cfdb6298ab3a5b2add12d74ac8b9f310fd59c936afe0d29a20d2e16448c38657 matched;
BridgeAlpha(7)=76/181JVM steps/direct+26q7 slices, BridgeBeta(8)=203/225 steps and
six refusals reproduced. Whole parent baseline2.039s/280317952B sampled groupRSS.

The genuine byte path is confirmed by source inspection and execution: fixture ZIP
bytes enter AS0; ZI0 and DI0 process them in EVM; ClassBridge STATICCALLs DI0 FINAL
read; its returned bytes enter the exact unchanged VFS0a start/resume ABI; the EVM
JVM parses/executes the generated Java. Host code never supplies raw class bytes to
that execution entry. Java8 is a separate generated-fixture oracle only.

## Limits of the original experiment

The unsafe/reflection use obtains the disposable DI0 session's StateDB pointer,
not decoded class bytes. SetCode is used ONLY to install the exact accepted oversized
LOCAL VFS0a engine at its frozen address; resources/pages/adapter are EVM CREATEd.
This is legitimate labeled test wiring, NOT an accepted transport API. After joining,
bridge/Java calls mutate that StateDB without per-call commit/reload/publication.
The report's resourceStateRoot is the earlier resource state root, not a published
post-Java shared-world trie. Failure probes also manually restore the host snapshot;
they are not an independent post-write EVM rollback/publication gate.

The adapter is stateless except owner. It revalidates caller-supplied resource roots
on every call; the existing JVM binds continuation to class bytes, while the driver
checks returned input binding. Production must define/pin the resource package per
instance rather than inheriting that driver-only source-binding check. No new live
ownership vulnerability is claimed from this observation.

## Reproduced valid-size blocker

_load allowed class sizes1..65536 but issued ONE DI0 read(0,size). DI0's accepted
single-read bound is4096. Parent constructed valid generated BridgeAlpha classfiles
with an ignored ParentPadding class attribute at EXACT sizes4096,4097,8193,65536,
65537. Java8 accepts all and returns76. The old adapter:

-4096 executes76/181 steps;
-4097,8193,65536 fail with genuine DI0Error(10) before JVM execution;
-65537 correctly fails BridgeError(8), the existing Java image limit.

The strict positive gate exits1; preserved single-read-failure.json/watchdog. Thus
the old result proves the295/301-byte fixtures, not arbitrary64KiB class intake.

Parent corrected ONLY its disposable copy to allocate the bounded class image and
issue chunks<=4096, length-check each returned fragment, then MCOPY those EVM bytes
into the buffer. No host plaintext/cap change. Instrumented EVM call-frame tracing
observes read lengths4096;4096+1;4096+4096+1; and16x4096. This trace is diagnostic
only, never input/output recovery. Four legal sizes now execute76/181 steps;65537
still rejects8 before any DI0 read. Exact65536 direct and26q7 slices have identical
terminal machine root/result/count. Largest measured direct padded call4698971gas.
Paged-size gate1.696s/26931200B; ordinary100M calls. Original3-success/6-refusal suite
also passes on the corrected artifact.

Corrected disposable runtime3978B SHAaa3f663e67279bc02bae4ba7e3afd0bdfa538fd91d1754378bd591e7859e5897;
init4021B SHA2b84525276ce3804bb8664537bc2ed7a15da24d5d2acc4732585316208391e7f;
sourceSHA900d3142cfb02cab56a7ed1cd07df14eba040366fc55e5af16dfdfaf83c87d99.
Pinned solc0.8.30,opt200,viaIR,Cancun,metadataoff. No production artifact changed.
Evidence/reproducer: evidence/java-evm/class-bridge/parent-e3f45ec22/.

Parent's final tracked fresh reconstruction ran6.751s/320335872B sampled groupRSS,
exit0 under20min4GiB. It rebuilt both artifacts/Java8 fixtures/Go drivers, reproduced
the old valid-size failure and passed the corrected boundaries/original suite.
The earlier oracle-output formatting assertion failure remains archived separately.

## Next dependency

Proceed with one bounded SHARED-WORLD preflight, not immediate production freeze:
new self-owned raw EVM database (no reflection/private-session pointer), constructor-
bound1..4 FINAL DI0 resource references totaling<=65536, paged EVM reads, unchanged
LOCAL VFS0a engine, fixed owner/no transfer/rebind, one JVM instance per coordinator.
Measure two-class linking/actual calls, q grouping, per-mutation commit/reload and
real disk/new-process continuation. See JAVA_EVM_MC_SHARED_WORLD_PREPARATION.md.

This must not change AS0/ZI0/DI0/VFS0a/engine quotas or pretend to be general Java
ClassLoader support. Original MinecraftServer/AbstractLogger bytes were decoded
previously by the parent, but NO original Java/Minecraft instruction executed here
or in the worker proof. No EULA, listener, world, Done or implicit push.
