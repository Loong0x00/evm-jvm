# Parent Class.asSubclass preflight

**Parent-verified unchanged worker semantics.** Evidence:
`evidence/java-evm/minecraft-entry/parent-fdb8b3155/`.

Bootstrap Class becomes1015B SHA
`8986691ab80193f6958d7560a09f44b9dbacb22a30b317b905c811a2bf440ff7`.
Ordinary generic `asSubclass(Class)` calls exact private-static-native
`asSubclass0(Class,Class)` global binding10 (separate from String-local10). Native
validates the entire canonical mirror set/name/defining-loader mapping, materializes
both hierarchy closures, and applies full `_typeAssignable` including interfaces.
Success returns the identical receiver with no allocation/initialization; null parent
raises guest NPE kind6 and nonassignability raises catchable CCE kind8 after consuming
arguments. Total71 and exception kinds14 remain.

Parent domain `MC-CLASS-AS-SUBCLASS-PARENT1` uses engine
`0x4d432d41535355422d504152454e540000000001`,370032B (23184B LOCAL384
headroom), SHA `575d889e860e0743386c3abe19659b9061a65d487ed65076f5f10d485e29157d`,
Keccak `adb3eee77f938193982453c060a44ada01d10eb7c29f7874e4813d2a5046c600`.
Coordinator4146B Keccak
`65c34d2702a85e9da394bfa4a884c4d5876f39cbd49239be3de1544a5b6dac74`.
Other70 images are byte-exact; accepted320 unchanged.

## Generated acceptance

Raw class→interface, interface self, Boolean→Object, exact/super CCE catch, null NPE
and identity converge q1/q7/direct at84J/5I, epochs84/12/1, machine
`54307dc663cec901fa17d7e033f63be360b3756d00235998c6cf75a3ac5d1d3a`, opaque
`8117728d272d11624940f27fe46e13e85dfaacd5e9032d488470125252864949`.
A target whose `<clinit>` throws completes untouched at9J/2I, epochs9/2/1. Uncaught
CCE converges at6J/3I, epochs7/1/1, lifecycle3/kind8, machine
`596e50bdc1ba7657fa8b41af78813854aa694e8790034ebf7ff4b468d819e5dc`, opaque
`7ba4d12ea7afbf0430e987926a98d0583a30f4007ae00335584d7d5fcbe13b9c`.
118 canonical focused receipts pass; isAssignableFrom/cast/newInstance remain omitted.

Integer/NFE replays retain3488 canonical receipts. Fresh retained asSubclass plus all
prior controls finishes q7/direct at4997J/33I, epochs714/2, machine
`23b90349ffeb791530e4784ea85e33763de7fdc0f96c95e551668bbaee9f9121`, opaque
`7dc1c34e845c04e8d6a11545ade933930bd95f0b0c19ef286ef3dd9d124ea638`;
723 canonical receipts pass. Direct uses954449271 gas, below the unchanged975M
execution ceiling after25M reserve. Whole source+all generated+NEW original gate exits0
in903.209823s with972791808B process-tree peak.

## Original and the now-measured raw-class cap

With the prior22 bindings, asSubclass succeeds and original reaches3010J, where ldc
needs same-JAR `DefaultFlowMessageFactory`. Its direct interface `FlowMessageFactory`
is also in the pinned JAR and needed for the next asSubclass. Parent therefore adds
both declared same-JAR EVM bindings—still within the accepted24/262144 profile—and
starts a fresh raw24 world. No class bytes are embedded in source/evidence.

Raw24 execution passes both factory asSubclass sites and continues hundreds of guest
steps. q7/continuation reaches epoch539/3773J/30I, then same-JAR
`ParameterizedNoReferenceMessageFactory` is required by StatusLogger `<clinit>` PC47.
This would be the25th raw class and cannot be declared under the current hard cap24.

Six successful q1 steps commit PCs41,44, nested constructor0/1/4, then PC47. Final
epoch545/**3779J/30I**, checkpoint22184B SHA
`c6b880c8a09098fa00a82f16b28c9170756019e0df6a82f8b1b996d7e91e732c`, root
`55b7c213fe38eead94a185f0c7aef398214e8c6d58599a1bc7ad42527d99a4b5`, machine
`6076fe140583be3e4ed1852021c1634fb3513f052e4e9f923ee4efa83ab7cf68`.
Next q1 repeats MissingClass context4103/site47, selector555db429, gas155931738,
Head/root unchanged.545 canonical original receipts pass.

Continuing now requires explicit amendment of raw-class cap24→25 (coordinator fixed
arrays/guards, engine MAX_RAW_CLASSES/config commitment, and driver guards) while
keeping262144B and all other limits fixed, or a much broader lazy archive Program-growth
mechanism. The former is the measured minimal change; neither is implemented here.
No Minecraft main body/world/Done.
