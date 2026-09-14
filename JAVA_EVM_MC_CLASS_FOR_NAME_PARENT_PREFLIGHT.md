# Parent bounded Class.forName(String) preflight

**Parent-verified with a Java8 image correction.** Evidence:
`evidence/java-evm/minecraft-entry/parent-69ea5129d/`.

Worker69ea5129d correctly adds ordinary public `Class.forName(String)` delegating to
private-static-native binding9. It reuses immutable Program dotted lookup, guest CNFE
kind13, mirror/frontier and OOM logic. Missing/malformed names raise catchable CNFE.
An already initialized present target returns its canonical mirror; an uninitialized
present target atomically reverts `ClassForNameInitializationError(target,pc)` before
mirror allocation. No three-argument overload, host lookup, lazy JAR load or fake
initialization exists. Total bootstraps68, exception kinds14 and bindings1..8 remain.

## Parent Java compiler correction and pins

The worker's 770B bootstrap39 image (SHA `d6378380...`) is exactly reproduced by the
host `/usr/bin/javac21 -source8 -target8`, not the required Java8 compiler. It is
major-version52 and semantically correct, but parent does not accept that toolchain.
Parent recompiles the same source with `/usr/lib/jvm/java-8-openjdk/bin/javac`,
`-source8 -target8 -g:none`, yielding670B SHA
`0e3d4ea717a8c96c75d6eca139874e100ab7e5700758dc14acd6ae47b84b7934`, and replaces
only `_bootstrapClass` before compiling Solidity.

Parent LOCAL384 pins:

* domain `MC-CLASS-FOR-NAME-PARENT1`, all nine; engine
  `0x4d432d464f524e414d452d504152454e54000001`;
* engine358672B (34544B headroom), SHA
  `3679f7f8bfe5aba518d57fc66a911984aa74853935349b8e11cc2e95e473c0c3`, Keccak
  `30321105b09bfcad9d2035bee963ee89a5ba371b91486838e5580e8374f51e8c`;
* ordinary coordinator4146B, Keccak
  `88874b48b0933fec2943cb0c2dac8d595da2628191f621a369b71b22bcf2e155`;
* bootstrap68/native1..9/exception kinds14; accepted320 unchanged.

## Generated acceptance

The combined parent probe now tests loadClass miss/malformed, forName miss/malformed
exact+ReflectiveOperationException catch, initialized raw-target canonical identity,
initialized Boolean bootstrap/null-loader identity, and every retained
Boolean/System/IAE/real EVM-ZI0 resource/URL/set/thread/PA/arraycopy control. q1/q7/
direct finish identically at3662J/26I, epochs3662/524/1, machine
`df378096408e52836c83cc80c50ffd0260f3cc39b694afe3171806b503ca28e2`, opaque
`b8258fbf5547b0bd060e26e183830629f5e2df08acbde91bc0c790abbfac6b7d`.

Uncaught forName miss terminates lifecycle3/kind13 identically at4J/3I,
epochs5/1/1, machine
`9483af22bd0c63dd7b57b67eb2acf3c7a7cc49513356b3e32f30ebd20154690b`, opaque
`e6a3c705edb67963cef8e56ff8756113c58153914c1564a728eb3bd28181a9a7`.
Present-uninitialized selector `b9587663` words1,1, omitted overload, raw Class and all
prior raw replacements refuse without root change. Canonical generated receipts pass.

The final fresh source-build+generated+NEW-original22 whole process tree exits0 in
1060.990102s with976830464B peak RSS, inside20min/4GiB. LOCAL1B,30s/call and25M
reserve remain exact; no failed checkpoint is reused.

## Original frontier

The unchanged original catches both loadClass and forName CNFE for absent
`javax.servlet.Servlet`, completes the web-app optional probe, and advances from2283
to2534J under q7. It then reaches `org/apache/logging/log4j/util/Constants.getMajorVersion`
with absent `System.getProperty("java.version")` and exact invokevirtual
`String.split("-|\\.")` at PC9. q7 refuses `StringProfileError(1,9)` selector
`32e310eb`, gas107250516, after epoch362/2534J/26I.

Two successful q1 checkpoints commit PC7 then PC9. Final epoch364/**2536J/26I**,
checkpoint16082B SHA
`66f1dd2349e93fae92e417eb27a06c3ff5431beb5ec75885ef3b49d9dd3cdd5b`, CP root
`77117a5bdb8a077a119b8ad940464bbaa5d8c9c0ed655425a9c9608ce06b66fb`, machine
`36aadbe6b453f0bbe84d04e3f5b65f8fe1523ff6c3a020794b8a0be06d8484ee`.
Next q1 repeats the same refusal, gas107704109, Head/root unchanged.364 canonical
original receipts pass.

The next stage must expose a deterministic guest `java.version` property and bounded
String split behavior; merely fixing null-receiver precedence would produce an
uncaught NPE before Constants' catch range and would not be startup progress. No
Minecraft main body/world/Done.
