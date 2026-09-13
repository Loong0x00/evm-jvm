# Resource enumeration preflight (worker scaffold)

This bounded LOCAL-only preflight starts from `3ca6e4322` and owns only
`evidence/java-evm/minecraft-entry/resource-enumeration-preflight/`. It must not
execute original Minecraft inputs. The intended bridge is a single immutable
ZI0-indexed archive presence query, returning an empty or one-entry guest
`Enumeration<URL>` only; it does not decode resource contents or implement
`URL.openStream`.

No result is claimed by this scaffold. The final evidence must pin a fresh engine,
coordinator, archive index, generated non-class resource, receipt chain, runtime
size/headroom and true whole-process-tree peak. Existing accepted 320 KiB limits
remain unchanged; this unaccepted LOCAL profile may use the authorized 384 KiB
installation ceiling and LOCAL1B external calls with the fixed 25M EVM reserve.
