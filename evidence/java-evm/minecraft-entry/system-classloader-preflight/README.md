# System ClassLoader getter evidence

This directory is the worker-owned reproducible source/evidence area for the
narrow `ClassLoader.getSystemClassLoader()` preflight. No original Minecraft
class or payload is included.

`source/engine` is the repaired defining-loader basis plus binding 6; its nine
engine domains are `MC-SYSTEM-CLASSLOADER-PREFLIGHT1`. `source/coordinator` is
pinned to the resulting engine code hash. The recorded 320 KiB compiler guard
fails at 328695 bytes (`artifacts/logs/320-cap-failure.log`), followed by the
explicitly labeled LOCAL384KiB artifact build. The compiler is solc 0.8.30,
optimizer 200, viaIR, Cancun and metadata off; Java images use Java 8.

`receipts/` contains all generated q1/q7/direct checkpoint and public receipt
files but excludes the disposable driver executable and every LevelDB/state
directory. `checks.py` verifies artifact/image pins, native source invariants,
q1/q7/direct canonical equality, and the two public refusal receipts.
