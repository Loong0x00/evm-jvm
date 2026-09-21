# Generated-only guest `Throwable.getStackTrace` preflight

This isolated LOCAL evidence stage implements the bounded follow-up in
`JAVA_EVM_MC_THROWABLE_GUEST_STACK_TRACE_PREPARATION.md`.  It is **not** an
accepted Minecraft/original-JAR replay, a full Java stack-trace API, a VFS change,
or a Done/EULA/world claim.

## Scope

* `Throwable.getStackTrace()` is exact public instance native binding 14 and
  snapshots only `frames[0..depth)` in the EVM interpreter.
* It returns a fresh top-first `StackTraceElement[]`; every element is fresh,
  carries the actual dotted `ClassInfo` name and actual method MUTF-8 name, and
  has `isNativeMethod() == false`.
* Only image 5 (`Throwable`) and image 90 (`StackTraceElement`) change. The
  verifier recomputes all 94 ordered leaf hashes from source and proves only
  slots 5/90 differ from `parent-afc1785d4`.
* `Thread.getStackTrace()` retains its prior ordinary Java zero-length fresh
  array behavior. StackTraceElement's direct native allocation and ordinary
  getter dispatch do not spuriously initialize the no-`<clinit>` leaf.

## Reproduction

Run from the repository root. All generated intermediates remain under ignored
`build/`; durable summaries are under `results/`.

```sh
B=build/java-diff-mc-throwable-guest-stack-trace-build-run1
F=build/java-diff-mc-throwable-guest-stack-trace-fixtures-run1
G=build/java-diff-mc-throwable-guest-stack-trace-gate-run1
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/build.py "$B"
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/generate_fixtures.py "$F"
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/gate.py "$B" "$F" "$G"
```

The gate executes only trusted generated Java-8 fixture classes. It checks
nested real frame order/names/methods, fresh arrays/elements, indexed access,
false native flags, q1/q7/direct/reopen equality, dormant images, raw replacement
refusals, and receipt re-encoding. It does not read an original artifact, JAR,
network input, Minecraft resource, world, or EULA.
