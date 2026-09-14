# Parent Number/NumberFormatException/Integer preflight

**Parent-verified unchanged worker semantics.** Evidence:
`evidence/java-evm/minecraft-entry/parent-661331e3d/`.

Worker661331e3d appends Number at68, NumberFormatException at69 and Integer at70.
Number is abstract Serializable with ordinary byte/short delegation; NFE extends the
reserved IllegalArgumentException; Integer is final Number/Comparable/Serializable
with value constructors/conversions/equality/hash/compare/bridge and decimal
`parseInt(String)`. Parsing uses Java's negative-accumulation overflow discipline;
null/empty/sign-only/non-digit/MIN/MAX overflow allocate and throw exact guest NFE.
All are ordinary Java8 `-g:none` images: Number376B SHA
`fe77f74edbcc2777f4edfa6227759fd8a3b856838113fb0fe9880affc4c9876f`, NFE164B
`a627a1649de875297f522fd2fde19f32b3e79f1945e7343941c696692e039d15`, Integer1667B
`bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537`.

The three names are reserved. Total71; global native bindings1..9, String-local10 and
exception registry14 remain unchanged because NFE is constructed/athrown by ordinary
bytecode. No host parser, radix overload, valueOf/cache or toString claim.

Parent domain `MC-INTEGER-PARENT1` uses engine
`0x4d432d494e54454745522d504152454e54000001`,367680B (25536B LOCAL384
headroom), SHA `004015f510957ad0e5707ee645077a9bedcfd415bd8a37bbfd734cad5d7de63a`,
Keccak `4a588cff342e2664ab01dec06c8d274ef861eca8104618192f7c239ce592806c`.
Coordinator4146B Keccak
`f899c1eef7185fff4782bc218b255049b243a640020caed59f35411b01201e14`.
Prior String/System/Class images retain accepted hashes; accepted320 is unchanged.

## Generated acceptance

Focused valid/invalid/constructor/Number/Comparable tests converge q1/q7/direct at
2676J/14I, epochs2676/383/1, machine
`7bbc1d1e57385a4a7da0fd63ef286a139a8f114674300683cdb35db17101f330`, opaque
`6ffe5e1c601a187cd1ad2d4af1b2d47f9d267d576cd6f7bc70ba7e493b1b9611`.
Uncaught positive overflow converges at372J/8I, epochs373/54/1, lifecycle3/javaKind0,
dynamic class `java/lang/NumberFormatException`, machine
`142ea8773fc6ac3d46886660feb8f41ea6c03c08460359c71f3b85c22864d2d4`, opaque
`93dced103f663e160a3dc9a40501b6fe1df83bdc5e0e7358f62e7c3fae15ef99`.
3488 canonical focused receipts pass; all three raw replacements and omitted radix/
valueOf refuse atomically.

Fresh retained q7/direct includes basic Integer/NFE hierarchy plus every split/OOM,
forName/CNFE, Boolean/System/IAE, genuine EVM-ZI0 resource/URL/set/thread/PA/arraycopy
control. It converges at4951J/32I, epochs708/2, machine
`9e9709101e6819d57eb4b5d034a31f3b88e48c48e8b8769fee13f23631ee1592`, opaque
`93bf284ef17eab542d8a8191bca756632c661259de755517a8c268a9388a4ff7`;
717 canonical receipts pass.

The first original harness checkpoint was successful but its read-only decoder still
bounded total classes at92; raw22+bootstrap71 requires93. Parent expands only that
test bound to95 and continues exclusively from the successful EVM checkpoint. Final
acceptance uses a wholly NEW world. Source-build+focused q1/q7/direct+retained controls+
NEW original whole process exits0 in757.521853s with968769536B peak RSS.

## Original frontier

Original22 parses both version components, completes Constants initialization and
progresses into AbstractLogger default message-factory selection. q7 reaches
epoch428/2996J/28I then exact CallError(3,36), gas119244648.

Six successful q1 steps reach AbstractLogger class6 method8
`createClassForProperty` PC36. Final epoch434/**3002J/28I**, checkpoint17152B SHA
`d45ebd710aedbf2d560426673c005f5b1a58a47029907a1552983a658fd58f92`, root
`cd133acc5021c9cf288f12205d4b9eac4491ffa7e1a328923c7844d2a267c9f0`, machine
`271799b765590668554b2aceeb198707037e88c05fcc6858dc11b07cb64f4328`.
Next q1 repeats CallError(3,36), gas117590931, Head/root unchanged.434 canonical
original receipts pass.

Javap identifies PC36 as exact `Class.asSubclass(Class)Class`: loaded
ReusableMessageFactory mirror against MessageFactory.class. Next adds identity-preserving
assignability and existing guest CCE kind8 only. No Minecraft main body/world/Done.
