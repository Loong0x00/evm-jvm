# Genuine guest OOM at MAX_ARRAYS=1024

Gas-only LOCAL uint64-max continuation of the unchanged original server from the authenticated P19 head is successful and deterministic: one q1 plus 32 q4096 slices advance 131073 JVM steps in173.740s, reaching 1,405,662 JVM /84 internal. The next successfully committed state is lifecycle3 with `java/lang/OutOfMemoryError` handle1974. Authenticated heap counters are ordinaryArrays=1024, ordinaryObjects=943, arrayElements=81133; source cap is exactly `MAX_ARRAYS=1024`. This is a genuine guest OOM caused by the interpreter profile, not host memory or EVM OOG. Evidence: `evidence/java-evm/minecraft-entry/parent-668583cae/u64max/`.

## One measured capacity change

Raise only `MAX_ARRAYS` from1024 to2048. `MAX_HANDLES` remains derived and grows accordingly; keep MAX_OBJECTS=1024, MAX_ARRAY_LENGTH=65536, MAX_ARRAY_ELEMENTS=262144 and every checkpoint field/limit otherwise unchanged. Existing uint16 ordinary-array counters can represent2048. No lazy arrays, failed-state recovery, fabricated allocation or Java semantic shortcut.

Generated ordinary controls must prove 1024 and1025 zero/small arrays allocate successfully, 2048 boundary and2049 typed guest OOM, exact checkpoint counters/reopen/q1/q7/direct where feasible, prior packed/sparse/malformed/Integer/Object/Math/raw71 controls, runtime<=393216 and each gate<=1200s. Parent fresh-domain rebuild/gate then replays the untouched original under LOCAL uint64-max gas, q<=4096, <=30s/call, using only successful checkpoints. Gas is a harness budget only; no standard-chain claim. No world/EULA/Done claim until genuinely observed.
