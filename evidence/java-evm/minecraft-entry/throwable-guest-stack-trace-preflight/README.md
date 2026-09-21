# Generated-only guest `Throwable.getStackTrace` preflight

This isolated LOCAL evidence stage implements the bounded follow-up in
`JAVA_EVM_MC_THROWABLE_GUEST_STACK_TRACE_PREPARATION.md`. It is **not** an
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

## Full generated gate

`tools/full_gate.py` combines the current focused q1/q7/direct/reopen snapshots
with the current parent-generated retained corpus. Retained rows use
direct/reopen where repeating historical q1 chains would exceed the fixed
20-minute limit; existing retained focused q1/q7/direct rows stay in the same
gate. The old empty-Throwable positive and `getClassName` omission are explicitly
superseded by the focused nonempty-frame checks, while the independent
four-argument constructor omission remains tested.

`full-gate-run3` passed in 852.8919992969604 seconds (<1200): 525 commands, 192
result rows, 153 canonical successful worlds, and 13,144 receipt re-encodings.
See `RESULT.md`, `results/gate-summary.json`, and
`results/full-gate-manifest.json` for exact inputs, hashes, receipts, and scope.

## Reproduction

Run from the repository root. All generated intermediates remain under ignored
`build/`; durable summaries are under `results/`.

```sh
B=build/java-diff-mc-throwable-guest-stack-trace-build-full1
R=build/java-diff-mc-index-out-of-bounds-string-constructor-fixtures-retained-full1
F=build/java-diff-mc-throwable-guest-stack-trace-fixtures-full1
G=build/java-diff-mc-throwable-guest-stack-trace-full-gate-full1
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/build.py "$B"
python3 evidence/java-evm/minecraft-entry/index-out-of-bounds-string-constructor-preflight/tools/generate_fixtures.py "$R"
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/generate_fixtures.py "$F"
python3 evidence/java-evm/minecraft-entry/throwable-guest-stack-trace-preflight/tools/full_gate.py "$B" "$R" "$F" "$G"
```

The full gate executes only trusted generated Java-8 fixture classes. It checks
real nested frame order/names/methods, fresh arrays/elements, indexed access,
false native flags, focused q1/q7/direct/reopen equality, direct/reopen retained
controls, dormant images, raw replacement refusals, and receipt re-encoding. It
does not read an original artifact, JAR, network input, Minecraft resource,
world, or EULA.
