# Class defining-loader preflight

## Scope

LOCAL-only continuation from `parent-cc0c40e71` / `67fe03fd1`: implement only
`Class.getClassLoader()` using an ordinary, checkpointed guest heap identity.
Raw supplied class mirrors must share one non-null VM-owned concrete
`ClassLoader` subtype; bootstrap mirrors must remain null. This is not resource
lookup, class loading, reflection, Minecraft execution, or Done.

## Frozen constraints

The basis is engine 326052 bytes, Keccak
`ca811ec4bf1be44d6a8a6469d38543cb8ba89b21c93589ba07338c1ed5b7f0df`, 51
bootstrap images and 1628 bytes of the LOCAL 320 KiB cap. The experiment first
records the unmodified 320 KiB cap result. If the complete validation cannot
fit, a separately labelled LOCAL 384 KiB copy may be built; 320 KiB remains the
accepted/production cap. LOCAL external gas is 1B with 25M reserve, 30 s call,
20 min / 4 GiB whole group, 24 classes / 262144 bytes, 128 frames, CP 4096,
Code 65535, heap/VFS/checkpoint 1 MiB and Head 32768 unchanged.

## Required semantics

The runtime derives raw membership from the immutable supplied package count,
not host names or catalogues. It derives the canonical loader by scanning and
validating ordinary heap objects, so there is no host side table. Restore must
reject absence, multiplicity, wrong dynamic class, alias/tamper, a raw mirror
with null/wrong loader, and a bootstrap mirror with a non-null loader. It must
not require mirrors for classes whose literals were never used.

Unsupported `ClassLoader` operations remain unsupported. `Thread` retains its
null context; LoaderUtil's fallback obtains the raw defining loader.

## Status

Implementation and generated-only proof are being prepared in
`evidence/java-evm/minecraft-entry/class-defining-loader-preflight/`. No
original Minecraft input, world, EULA, listener, resource lookup, startup, or
Done claim is included.

## Measured generated-only result

The reproducible source build stayed inside the first 320 KiB cap at 327658 B
(22 B headroom): SHA-256
`8ce10b67476572a0db39e076e48ac631fd29b97de409d40cd73ddaece9734db6`,
Keccak `d611ea952478718292318848a363cbe828f3fb2f91da54241bc9c7885a8e8a94`.
No 384 KiB copy was used. The 52nd bootstrap is 143 B `VMClassLoader`; the only
changed prior image is the 440 B `Class` image. The first generated two-raw
mirror fixture reaches VOID with q1/q7/direct at 88/13/1 epochs, respectively,
with equal 88 Java / 2 internal steps, machine root and opaque checkpoint.
`ClassLoader.getSystemClassLoader` remains an unchanged `CallError(3,0)` refusal.

The checkpoint validator contains the raw/bootstrap loader scan and rejection
logic, but this worker did **not** run a separate direct-EVM checkpoint-byte
tamper harness. That missing dynamic negative is explicitly recorded in
`artifacts/results.json` for parent review; it is not claimed as a pass.
