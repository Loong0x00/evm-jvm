# Parent ClassLoader.getSystemClassLoader preflight

**In progress; worker result is not acceptance.** Worker964258f2a/bc4aa5f31
integrated locally. Parent renamed the worker's evidence `tools-driver.go` to
`.go.txt` so normal Go package discovery does not treat it as repository code.
Evidence/recipes: `evidence/java-evm/minecraft-entry/parent-bc4aa5f31/`.

Candidate changes ClassLoader image to exact public static native zero-argument
getSystemClassLoader and adds binding6. Parent review confirms prior native1..5
selection/semantics remain, binding6 requires exact class/name/descriptor/access/
return, normal active-use initialization, `_push` stack capacity, and scans the
existing nonnull unique concrete loader without allocation. No resource method.

Worker again compacted unrelated `_classNameUnits` formatting. Parent restores
exact prior formatting before compilation; no semantic validation is removed.
All nine domains/address/owner/store are replaced with parent identity.

Existing320KiB must fail first; the exact same source then uses separately labeled
LOCAL384KiB, accepted320 unchanged. Parent independently compiles the195B
ClassLoader image, runs one outer20min/4GiB source-build/generated/original22/q1
gate, and retains1B/30s/25Mreserve plus all other limits.

Worker candidate pin for comparison only:328695B, SHA
`0f7c5fdf07a9cff27c1030dfd72b04dd1f6b9e05aa301449908fa41d06a6e8d6`,
Keccak `dbbd4e3ec0d7346164b514671918ee8410b08947568977b34a1eec7663475211`.
Generated identity/reopen and unsupported getResources/VM override controls are
rerun under parent pins before any original input. No fake empty resource result,
original payload archive, core/ABI/Makefile/push/main-body/Done claim.
