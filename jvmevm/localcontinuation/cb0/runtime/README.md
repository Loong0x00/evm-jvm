# MC-CB0 coordinator runtime candidate

Status: **frozen implementation candidate, not accepted**. `CB0ClassCoordinator`
binds one owner and one ordered package of one to four FINAL DI0 class resources.
It rechecks dependency identities, EVM-reads each class in at-most-4096-byte
fragments, and passes the assembled bytes only to the fixed LOCAL VFS0a ABI.
It has no registration, rebinding, raw-class execution API, events, fallback, or
receive function.

Build with the pinned compiler and settings:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm run check
```

The build enforces the exact constructor/error/ten-function ABI, no immutables or
link references, runtime at most 24,576 bytes, and init plus the 2,016-byte
maximum constructor ABI input at most 49,152 bytes. Generated split artifacts and
the combined artifact are committed so transport code can consume only the
embedded, defensive-copy `Artifact()` JSON.

This candidate is a LOCAL controller only. The separately installed 292,968-byte
VFS0a engine is not a standard CREATE deployment claim. It does not execute
original JAR classes, Minecraft, EULA, a listener, or a world.
