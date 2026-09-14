# Bounded guest Number/NumberFormatException/Integer preflight

**PARENT RESULT:** accepted unchanged after independent source/generated/original gates.
Original reaches3002J at Class.asSubclass. See JAVA_EVM_MC_INTEGER_PARENT_PREFLIGHT.md.

## Worker implementation record

This worktree is pinned at `512864d47`.  The implementation archive is confined to
`evidence/java-evm/minecraft-entry/integer-preflight/`; it starts from the parent-restored
java.version/split engine source and appends only Number, NumberFormatException and Integer.
No original JAR, Minecraft class, world, EULA, or startup input is included here.  Generated
and original continuation gates remain to be run from fresh local stores; no acceptance claim
is made by this record.

## Worker result (unaccepted parent handoff)

The copied engine now has a distinct nine-domain `MC-INTEGER-PREFLIGHT1` commitment,
new fixed engine/owner addresses, and append-only bootstrap positions68/69/70.  Fresh
Java8 `-g:none` images are Number376B
`fe77f74edbcc2777f4edfa6227759fd8a3b856838113fb0fe9880affc4c9876f`,
NumberFormatException164B
`a627a1649de875297f522fd2fde19f32b3e79f1945e7343941c696692e039d15`, and
Integer1667B `bc07a956ca5c0739fc6a476c53755b4b3658caf3496e00b912b44e9aa52e4537`.
The inherited String1015B, System825B, and Class670B pins remain exact.

Fresh generated q1/q7/direct/reopen runs of `IntegerProbe` agree:2676J/14I,
epoch2676/383/1, terminal result0, machine root
`0xd9268a5cc5bfb5e1f2acccad353382b80a5445c737a5d3dfcf822cbe25cf08a8`, and
opaque SHA-256 `bb18e800ecf5e0f454c537ffa4fd6c2abe918bc138780c01864b014ebe6a545d`.
The probe covers valid1/8/+7/-0/MIN/MAX/zeros, null/empty/sign/non-digit/overflow
NFE, NFE-as-IAE, constructors, Number values, equality/hash/compare and the
Comparable bridge.  A separately fresh uncaught NFE run agrees q1/q7/direct at
372J/8I, lifecycle3, dynamic class `java/lang/NumberFormatException`, machine root
`0x056d51ff29b5bb1b387a758aaa98b7088da4f277e3e3ed9f298af2d59973318b` and opaque
SHA-256 `d8572dcc4f25b3efc19f2af3ecc561f14a8d9a54c6b3e7013cefed2b5e4d7fc7`.

Fresh source rebuild pins engine367680B SHA-256
`9c776757d240ced1aa03d952a7a55a271be0e5ff6969001a388a8fe6b48b8a06` and
Keccak `efd59eb674a4bfb08c93af7055d43965d7b7f800964e6335c652b7802f1896f4`;
coordinator4146B Keccak
`f5261383421d78ea394c187d37d10a257fbc99b9b4ee8cbca35c8011a7e70202`.
The generated archive contains source images, artifacts, generated class resources,
full receipt/checkpoint archive, and logs, explicitly excluding Go binaries, LevelDB
and any original payload.  This is a worker handoff only: all-prior aggregate controls and the NEW original22 continuation remain parent-owned and
were not run.  Raw Number, NumberFormatException and Integer replacement inputs were
separately refused with BootstrapProfileError(1,1), unchanged roots; their receipts are
archived alongside the generated terminal receipts.
