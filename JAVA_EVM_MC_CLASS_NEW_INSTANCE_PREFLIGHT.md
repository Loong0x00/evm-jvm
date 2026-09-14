# Class.newInstance generated preflight

Worker source commit is `85005e73a`; generated evidence commit is `c4da5cd11`. Basis is `a0cfa9bc1` and
accepted raw-cap25 evidence. The isolated source/evidence directory is
`evidence/java-evm/minecraft-entry/class-new-instance-preflight/`.

The generated Java8-only run rebuilt the 1171-byte replacement `Class` exactly as
SHA256 `2cd0cbf46c408cff70c8dc8a4ac8b6f3e5a153162f4a42b5afc9f59bad360e8a`;
the bootstrap count remains71. Engine is 374848 B, SHA256
565371d68ef8180583fc29d05909bb4a60031772d6d7ca2df57cc5aae7ec14da,
Keccak a3db4ed598190f09f38ae3f77fc3c95e465f37d5d2f0c34819fcd63123189a73;
coordinator is4146 B, Keccak
1dab1b66023472ddff283171d8c04b4d65aed4d5c03546a83ec2da7e015c3de2.

The generated source gate passes success and caught-null NPE at q1/q7/direct4096,
with reopen each time. Success terminal roots/opaque payloads agree: 64 Java and
4 internal steps, q1/q7/direct epochs64/10/1. The Java assertions prove target
`<clinit>` exactly once, two distinct constructor results and target field writes;
checkpoint inspection records target static initialized=1 and constructed=2.
Null catches NPE and records result7 (11/3 steps; epochs11/2/1). Bootstrap,
abstract and public-class/private-zero-constructor cases revert deterministic
`ClassNewInstanceProfileError` selector 0xc6254057 before a checkpoint/head
mutation. Full receipts/worlds/LevelDB and binaries remain ignored; retained old
Class.asSubclass/Integer controls and a practical OOM exhaustion loop are not
claimed by this worker and require parent gate completion.

No original Minecraft JAR/class/resource/page/world was accessed or archived.
