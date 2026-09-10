# MC-VFS0a local continuation runtime candidate — size blocked

`VFS0aInterpreter.sol` is a production-integration candidate forked from accepted
MC-IOE0 at `cca4841`. It keeps the IOE0 JVM and appends the frozen eight Java 8
File/stream images after all 30 IOE0 images. The candidate implements the frozen
`JVMVF0A1`/`VFA1` 280-byte envelope, 17-field result, seed/config/machine/VFS/file
commitments, EVM parsing and canonical encoding, bounded inodes/file bytes and
identity-gated File/FIS/FOS native effects. It does not use the standalone
prototype action ABI or host-supplied binding metadata.

## Frozen bootstrap provenance

The 38 embedded images are checked by `build.js`. The final eight occupy slots
30..37 in this order: AutoCloseable, Closeable, Flushable, File, InputStream,
OutputStream, FileInputStream, FileOutputStream. Their decoded class bytes total
5976 bytes and retain the hashes frozen in `JAVA_EVM_MC_VFS0A_PLAN.md`. All 30
preceding IOE0 image hashes and slot identities are unchanged.

## Measured acceptance blocker

With the required compiler settings (solc 0.8.30, optimizer 200, via-IR, Cancun,
metadata disabled), this integrated candidate is **287440 bytes**, SHA-256
`03d502fa3bf036d997891d5e43bfb4852052ed3d7e5c29ab8cc213283e395bd6`.
Source SHA-256 is
`e84afe936f561415c06b8937aecd2cf0f38f42825e51c1e86c5f2161af5e3f2e`.
It exceeds the frozen 256 KiB (262144-byte) LOCAL acceptance cap by **25296
bytes**. This is therefore not a VFS0a acceptance artifact and no runtime tests,
Minecraft/JAR execution, EULA acceptance, listener, or startup claim are made.

Normal build/check commands deliberately fail on the cap:

```sh
npm ci --ignore-scripts
npm run build
npm run check
```

The checked-in over-cap runtime, ABI, and combined provenance artifact can be
reproduced or checked only with explicitly named measurement modes:

```sh
npm run measure-over-cap
npm run check-over-cap
```

Those modes report `acceptanceCapPassed:false`; they do not raise or waive the
cap. A parent scope/module/code-size decision is required before this candidate
can proceed to harness or independent acceptance gates.
