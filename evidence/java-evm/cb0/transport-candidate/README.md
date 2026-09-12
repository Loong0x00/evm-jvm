# CB0 transport candidate

Transport implementation candidate from `23d28e13d`, pinned against the real
runtime artifact at `4c8199db4` (runtime evidence head `5c378f934`). Compilation
used an ignored, disposable `build/java-diff-mc-cb0-harness-overlay/` tree
containing that exact committed runtime; the production runtime directory in this
worktree was not written.

The focused tests prove the transport's atomic fresh initial root (LOCAL engine
SetCode plus one ordinary AS0 CREATE), disk reopen without a repair CREATE, and
artifact/cap loading. This is candidate evidence only, not CB0 acceptance and not a
class/ZIP/Minecraft execution claim.
