# System.arraycopy COPY preflight

**Unaccepted generated-fixture candidate only.** This is the isolated derivative of
parent-verified marker-map `25b1f35a0`, at base `1e4027b9b`; it does not select,
read, parse, package, or execute an original JAR. Parent alone retries original13.

## Narrow delta

`evidence/java-evm/minecraft-entry/arraycopy-preflight/` adds the reserved,
non-overridable Java-8 `java/lang/System` bootstrap at appended bootstrap-root
position 44 (all existing positions 0..43 stay unchanged). It exposes precisely:

```
public static native void arraycopy(Object src, int srcPos,
                                    Object dst, int dstPos, int length)
```

The declaration is a real owned bootstrap classfile, pinned from its source;
there is no host Java call or evaluator. The bounded EVM implementation is the
one exact native binding. It copies raw primitive cells only between equal
primitive leaf kinds, preserving long/float/double cells, and has distinct
boolean, byte, char, short, int, long, float and double paths. Reference arrays
copy element-by-element through the existing component check. Thus a bad
reference element leaves the valid prefix and raises guest ArrayStoreException.
Same-array overlapping ranges choose backward or forward traversal as memmove.
Null precedes structural/range checks; non-array, primitive/reference, and
different primitive leaf failures are guest ArrayStoreException; structural-success
bad positions/length are guest ArrayIndexOutOfBoundsException. No System clock,
I/O, property, environment, Thread, ClassLoader, reflection or other API is
added.

The profile rejects caller-supplied `java/lang/System`, derives the conditional
Runnable/Class tail as before, appends System after map classes, and changes all
candidate domains/store format to `MC-ARRAYCOPY-PREFLIGHT/.../v1`. Old
checkpoints/cross-code execution are intentionally incompatible. The corrected
parent bounded metadata driver is retained as the predecessor: no read/process
history is placed into Head, and this candidate does not raise its 32768-byte
Head cap.

## Pins and limits

Source-only build pin: solc `0.8.30+commit.73712a01.Emscripten.clang`, optimize
200, viaIR, Cancun, metadata off. The exact LOCAL initial-state engine (not
CREATE) is `0x4d434d41524b45524d4150000000000000000001`; controller and
resources use ordinary CREATE.

* engine: 314445 B, SHA-256
  `bd937b517bde7ab82e55e8cf4576a3d9bbd9f9e2997dfa253d916a7fb8d321e3`,
  Keccak `e26868d0da83a19f81db91913b72f0b8e64141c660dcd9fd4ab9c1faa01ef5ba`;
* coordinator: 3547 B, Keccak
  `4f20d3f559992bb986d66e94b56286a5eae0e3c2ec8d5349e066c0f725abe2b8`;
* System.class: 196 B, SHA-256
  `9916a91aa97037cf42c64641ddea0ca4b0c4c0f8c5a4e921307da556cc516a92`.

The 16/262144 input cap, CP4096, Code65535, heap/VFS/frame/1MiB checkpoint,
100M ordinary gas/25M reserve, 30 seconds, and 320KiB engine cap are unchanged.
No accepted artifact, ABI, quota, Makefile, core, or profile is changed.

## Generated evidence and current blocker

`ArraycopyMain` is compiled with `javac --release 8 -g:none` and independently
runs as a TEST-only host oracle. Its opaque ZIP has only generated
`ArraycopyMain`, `$A`, `$B` classes (1964 B total); it checks reference distinct
and both overlap directions, offsets/exact-end zero length, null/type/bounds
precedence, partial ArrayStore prefix, primitive/reference mismatch, successful
all-eight primitive kinds including raw NaN and signed-zero float/double cells,
and retained small Map/class-literal controls. Execution input goes through EVM
AS0 -> ZI0 -> DI0 metadata/DEFLATE/CRC/final <=4096-byte reads, not host ZIP or
class parsing.

Durable receipts are under
`evidence/java-evm/minecraft-entry/arraycopy-preflight/actual-receipts/` with
SHA256SUMS. One whole session-owned process-group watchdog (20 minutes/4GiB,
file-backed command logs; no per-command session/timeout) completed in
198.491608 s at 885276672 B sampled RSS. q1 and q7 each reached Java VOID and
fresh-process reopen; q1 was 176 epochs/176 Java/3 internal and q7 25/175/3.
This **does not pass equivalence**: their machine roots differ, so the one-Java-
step quantum divergence is retained as the next candidate defect rather than
hidden by an assertion or quota change. q4096/direct instead retained its actual
pre-checkpoint EVM panic `0x4e487b71/0x32` at 18,537,604 gas with unchanged root;
it is not claimed as a direct proof or rescued with 1B gas.

Consequently this is usable source/evidence for parent diagnosis only, not an
arraycopy acceptance, original Minecraft execution, EULA/world/Done claim, or
promotion.
