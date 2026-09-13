# PrivilegedAction preflight evidence

This directory is a generated-fixture-only, source-only LOCAL preflight.  It
adds exactly the Java 8 interface `java/security/PrivilegedAction<T>` with the
single erased method `()Ljava/lang/Object; run`, as bootstrap image 48 after
the parent basis's 48 images.  It is not `AccessController`, a security
framework, a `SecurityManager`, a permission API, a `ClassLoader`, a resource
lookup, or Minecraft execution.

`gate.py` is the sole reproducer. It copies only the explicitly named
`parent-2293e298e/{engine,coordinator,pins.json,executed_driver.go.txt}` basis,
compiles the owned interface with the pinned Java 8 compiler, applies a narrow
source transformation, builds with solc 0.8.30/optimizer 200/viaIR/Cancun/no
metadata, and runs generated Java controls through the EVM driver.  It never
opens an original JAR, class, world, resource page, or LevelDB directory.

The gate uses an absolute fresh ignored `build/java-diff-mc-privileged-action-*`
directory. It has one inherited process group, one 20 minute/4 GiB budget, and
file-backed logs. `artifacts/` is populated only after a successful run and
contains no Go binary or LevelDB data.
