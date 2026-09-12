# Generated Java `main(String[])` CB0 preflight

This is a **generated Java 8 preflight**, not an engine or CB0 change and not a
claim that CB0's fixed `int` root ABI directly accepts `void main(String[])`.
It answers the narrower question: can a generated guest `int Launcher.run(int)`
allocate a real `String[]`, call another generated class's public static
`void TargetMain.main(String[])`, and return observed guest state only after that
void call returns? The final replay says yes for this fixed two-class package.

`Launcher.java` selects empty, ASCII, or Unicode arguments, constructs the guest
array, and invokes `TargetMain.main`. `TargetMain` has observable static
initialization (`state=11`) and mutates it in `void main`. Mode 3 calls
`TargetMain.main(null)`: the resulting terminal EVM guest exception is pinned
canonical Java kind 6 (`NullPointerException`), not an EVM error/OOG. `Oracle.java`
is a separate Java8 host-test-only oracle and is deliberately excluded from the
uploaded ZIP.

## Measured final replay

`final-report.json`, `final-fixture.json`, `final-replay.log`, and
`final-watchdog.json` are the captured clean run. Compiler is
OpenJDK Java8u504 (`javac 1.8.0_504 -source 8 -target 8 -g:none`). Deterministic
ZIP SHA-256 is `4eae36f7769eee73ea7c6646d85995cdf3e087e8d9e624989d13ef2af256f928`;
its only entries are generated `Launcher.class` (417 B) and `TargetMain.class`
(378 B). The archive is not committed because `generate_fixture.py` reproduces
it and its hash is verified.

Observed guest results match the independent Java8 oracle:

| mode | guest behavior | result/outcome | JVM/internal steps | Java-call gas |
|---|---|---:|---:|---:|
| 0 | empty `new String[0]` | return 341 | 24 / 4 | 6,312,798 |
| 1 | ASCII `{"ASCII","arg"}` | return 381 | 54 / 4 | 8,363,235 |
| 2 | Unicode `{"λ","☃"}` | return 351 | 57 / 4 | 8,356,038 |
| 3 | `main(null)` | terminal kind 6 NPE | 22 / 5 | 5,451,060 |

For mode 1, direct/q7/q1 complete at 1/8/54 slices respectively. All final
machine, VFS, AS0 content, ZI0 index, FINAL DI0 resource, and EVM-derived
package roots agree across those groupings. q1 uses 54 distinct Start/Resume
child PIDs plus a separate terminal-reopen PID; setup, Start, every Resume, and
terminal reopening are separate processes;
every reopen asserted `Initialization().EngineInstalled == false`. Each
successful Java call had exactly one nested pinned-engine checkpoint event and
a terminal checkpoint whose EVM Keccak plus defensive SHA-256 were verified.
All recorded Start/Resume calls stayed under ordinary 100M gas; no 1B boundary
call was used. The complete replay watchdog was exit 0, 6.133 s and sampled
peak process-group RSS 334,929,920 B under the required 20 min/4 GiB bounds.

## Reproduction

Run only with a nonexistent ignored output directory:

```sh
python3 evidence/java-evm/watchdog.py build/java-diff-mc-main-entry.log \
  build/java-diff-mc-main-entry-watchdog.json \
  bash evidence/java-evm/main-entry/preflight/reproduce.sh \
  "$PWD/build/java-diff-mc-main-entry-NEW"
```

The script scopes `TMPDIR` to that output, makes the fixture, copies the archived
`.go.txt` driver into it, builds it, and uses only public `cb0.Session` methods.
The execution driver treats the ZIP as opaque bytes; it neither opens a ZIP nor
parses/inflates/catalogues class data. It uploads the entire ZIP through
AS0/ZI0/DI0, asks only EVM `Head` metadata for known fixture bindings, builds the
ordered package assertion with frozen CB0 domains/pins, and lets CB0 make all
JVM class bytes from FINAL DI0 paged reads. It does not use raw-class input,
reflection, unsafe/private Session fields, StateDB manipulation, SetCode, or a
host Java evaluator.

`verify.py` rejects a wrong oracle/hash/result/typed NPE/checkpoint/PID sequence,
nonordinary gas, root mismatch, or engine reinstall. The initial actual CB0
package-assertion refusal is retained in `initial-package-pin-refusal.log`.

## Boundary and next dependency

A future launcher can remain an extra generated wrapper and invoke an unchanged
target JAR's declared `main(String[])`; this preflight does **not** add a root
ABI, dynamic/transitive loading, JAR discovery, or a general ClassLoader. It
also does not solve CB0's fixed <=4 images/<=65536 aggregate package frontier,
class caps, target dependencies, logging/platform APIs, or any Minecraft
instruction/startup/EULA/listener/world/Done work. The next dependency is a
separate bounded generated link/transitive-loading preflight before any original
JAR execution claim; it must preserve CB0/profile/quota limits.
