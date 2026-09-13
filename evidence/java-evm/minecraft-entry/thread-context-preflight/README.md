# Generated Thread context preflight evidence

Generated-only LOCAL evidence from exact ClassLoader parent `parent-d19622e52`.
It never reads an original JAR, class, page or world. `gate.py` copies the parent
engine/coordinator/driver only, appends bootstrap image 50, and runs generated
Java 8 fixtures in a fresh ignored `build/java-diff-mc-thread-context-*` path.

## Narrow result

The added `java/lang/Thread` is 450B, SHA-256
`4c76217e07b547c39ef42523e3cef55af582541265882b6998332124b3f72cb5`.
It has a private Object constructor, exactly one static `CURRENT` constructed in
`<clinit>`, and one nullable `contextClassLoader` field. Its only public surface
is `currentThread()Thread` and `getContextClassLoader()ClassLoader`. No host
callback, setter, start, scheduler, ThreadLocal, loader operation or resource
result is present.

The isolated engine uses address `0x4d432d5448524541442d434f4e544558542d3031`,
owner `0x4d432d5448524541442d4354582d4f574e455202`, and all-nine-domain
`MC-THREAD-CONTEXT-PREFLIGHT1`. Runtime is 326052B (1628B below the 320KiB
LOCAL cap), SHA-256
`d11b3725ba5151fbfc12011a5df87741cd3c80114eaafb1e056157736b8ea86c`,
Keccak `ca811ec4bf1be44d6a8a6469d38543cb8ba89b21c93589ba07338c1ed5b7f0df`.
The ordinary-CREATE coordinator Keccak is
`7c16213411499ea7fd34fc4da229122e244bbf937a8d76a3e1ef96bddc01852a`.
All 50 previous bootstrap images are byte-identical.

q1/q7/direct/reopen complete genuine VOID at 291 Java/7 internal steps, with
the same machine root
`0xb366bd14d9d38d656456dbcc3a2f83b46dbab0464241e9a6aad85c4e2c3761a0`
and opaque SHA-256
`bd1f32bcf961edc9a224aef61d8e3d8e539639f5160f0556a22255eda0cf4db2`.
The host-only generated oracle observes identity but reports its own installed
loader; the EVM fixture intentionally verifies the no-installed-loader default
null profile. Caller Thread replacement rejects with `0x6a23ad80`; absent
Thread setter/start and ClassLoader getter each reject with `0xd631c3a4`, all
with unchanged roots.

The successful whole gate's observed **true outer-group high-water mark** was
884120KiB. It uses one inherited outer group, no `start_new_session`, no
per-command peak reset, 30s calls, 20min/4GiB group bounds, LOCAL1B supplied
gas and unchanged 25M reserve/other limits. `artifacts/` contains full generated
sources/artifacts, Java sources are retained above, and receipts/logs/checkpoint
ranges are allowlisted; no Go binary, LevelDB or original payload is archived.

This is not an original22 replay, class loading, Minecraft main-body/world/EULA,
or Done claim.
