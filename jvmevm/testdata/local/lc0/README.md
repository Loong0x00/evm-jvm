# MC-LC0 trusted fixtures

These are the five exact trusted Java 8 classfiles copied read-only from the
accepted LC0 preflight evidence. They were compiled with:

```text
javac --release 8 -g:none
```

`manifest.json` pins class SHA-256 values, ordered bundles, entries, arguments,
and the Java 8/Java 21/accepted-monolith results (15, 36, and 10). The LC0 host
transport supplies these bytes unchanged. It does not parse or translate them.
`LC0AliasBox` and `LC0InitDep` are dependencies, hence five raw classes cover
three roots.

This corpus is continuation evidence only. It is not Minecraft execution, a
Java SE claim, EULA acceptance, VFS, networking, or a listener.
