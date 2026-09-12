# MC-CB0 runtime candidate build record

Status: **candidate only; not accepted**. This record pins the reproducible
controller source and generated artifact initially built on the CB0 frozen revision.
It does not record a transport acceptance, original-JAR handling, Java/Minecraft
execution, EULA acceptance, listener, world, or `Done` marker.

Run `./reproduce.sh` from this directory's repository checkout. It uses the tracked
`jvmevm/localcontinuation/cb0/runtime` source and exact local npm lock, rebuilds,
checks generated artifacts, and prints fresh SHA-256 sums. `build-check.log` is the
first generated-artifact consistency check; the committed `SHA256SUMS` gives the
corresponding source and output hashes.
