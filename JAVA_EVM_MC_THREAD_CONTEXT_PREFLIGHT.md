# Thread current/context-loader preflight

**PARENT RESULT:** independent source-only build/replay passes. Original22 now
commits the single Thread/currentThread/default-null context path and reaches
Class.getClassLoader at PC16. Parent removed an accidentally archived `.pyc`.
See JAVA_EVM_MC_THREAD_CONTEXT_PARENT_PREFLIGHT.md. Worker claims remain evidence.

Unaccepted LOCAL generated-fixture preflight from the exact parent ClassLoader-type
basis `parent-d19622e52`; this is neither class loading nor Minecraft execution.
The measured original22 continuation has committed 1752 Java steps/14 internal
steps. Its next missing owner is `java/lang/Thread` at typed
`LoaderUtil$ThreadContextClassLoaderGetter.run` PC0. Static Java 8 inspection
establishes the contiguous call pair `Thread.currentThread()` then
`Thread.getContextClassLoader()`.

## Only semantic delta

Append bootstrap image 50, preserving all 50 earlier image bytes and order:

```java
package java.lang;
public class Thread {
    private static final Thread CURRENT = new Thread();
    private ClassLoader contextClassLoader;
    private Thread() { super(); }
    public static Thread currentThread() { return CURRENT; }
    public ClassLoader getContextClassLoader() { return contextClassLoader; }
}
```

This creates exactly one guest object through normal guest static initialization,
`new`, and `Object.<init>`. The nullable field has Java's default `null`; no
host callback or installed loader exists. The original LoaderUtil fallback must
therefore execute. The candidate reserves caller replacement for Thread and
leaves existing ClassLoader type-only, PrivilegedAction, System getter/arraycopy,
and Properties behavior unchanged.

No setter, `start`, `join`, interrupt, sleep, scheduling, ThreadLocal,
concurrency primitive, `Class.getClassLoader`, ClassLoader method,
AccessController, resource enumeration, fake empty result, LoaderUtil substitute,
or original artifact is permitted. Missing/unsupported Thread members retain the
ordinary EVM member-resolution refusal.

## Isolation and bounds

The parent engine is 323026B (SHA-256
`c0e9d627b5709f9635731f6d85159b9d33079c33fd1876cbe7b6a258c5912a7b`,
Keccak `35f8925e4f8631a9ff23cb5faec1ed6c4db2c0e3d318c9fa21c70693e69a0258`),
with 4654B to the 320KiB LOCAL cap. The candidate must replace all nine engine
domain strings, engine address/owner/other/store and all driver pins; it must
not reuse any old checkpoint. Engine code is LOCAL initial state only;
coordinator, resources and stores use ordinary CREATE.

Use the user-authorized LOCAL1B external ceiling, not 100M, with 30 seconds per
call and one 20 minute/4GiB process group. Preserve 25M reserve, 24/262144
inputs, MAX_FRAMES=128, CP4096, Code65535, heap/VFS limits, 1MiB checkpoint,
32768B Head and 320KiB engine cap. A size failure is evidence, not authority to
raise or minify limits.

## Required generated gate

The durable gate/evidence must compile only generated Java 8 fixtures, build
with solc 0.8.30 optimizer200 viaIR Cancun metadata-off under a fresh absolute
`TMPDIR`, and archive source, artifacts, fixtures, canonical ABI events,
checkpoints, read ranges, logs and hashes. It must not archive Go binaries,
LevelDB, original JAR/class/pages or worlds.

Controls: repeated `currentThread` identity; exact static initialization/object
identity; default-null getter; explicit unsupported setter and start refusal;
caller Thread replacement refusal; and retained ClassLoader-array/type,
PrivilegedAction bridge, System, Properties and arraycopy controls. q1, q7,
direct and reopen must agree on VOID/sentinel/machine/opaque terminal data and
canonical receipts. Host Java is a generated-fixture oracle only. Parent alone
may run original22 q7, preserve that failure, and q1; failed traces are never
state authority.

## Generated-only result

`thread-context-preflight/gate.py` completed from fresh generated inputs. Thread
is 450B SHA-256 `4c76217e07b547c39ef42523e3cef55af582541265882b6998332124b3f72cb5`.
All prior50 images remain exact. The fresh engine is 326052B (1628B headroom),
SHA-256 `d11b3725ba5151fbfc12011a5df87741cd3c80114eaafb1e056157736b8ea86c`,
Keccak `ca811ec4bf1be44d6a8a6469d38543cb8ba89b21c93589ba07338c1ed5b7f0df`;
the coordinator Keccak is
`7c16213411499ea7fd34fc4da229122e244bbf937a8d76a3e1ef96bddc01852a`.

q1/q7/direct/reopen each reaches VOID at291 Java/7 internal steps with equal
machine root `0xb366bd14d9d38d656456dbcc3a2f83b46dbab0464241e9a6aad85c4e2c3761a0`
and opaque SHA-256
`bd1f32bcf961edc9a224aef61d8e3d8e539639f5160f0556a22255eda0cf4db2`.
Caller replacement rejects `0x6a23ad80`; unsupported Thread setter/start and
ClassLoader getter reject `0xd631c3a4`, all root-unchanged. True outer-group
peak was884120KiB; it is a high-water mark across all commands, not a
last-child report. No failure occurred in this generated gate.

No main body, world, EULA, listener, original22 replay, or Done claim follows
from this preflight.
