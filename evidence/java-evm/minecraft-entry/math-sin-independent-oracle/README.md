# Independent generated-input `Math.sin` oracle (research only)

This directory is a standalone Java 8 host oracle and a test-only numerical
exploration for the next genuine `Math.sin(D)D` blocker. It is deliberately
independent of the guest runtime: no Solidity, bootstrap, interpreter, active
stage, or runtime source is changed or used. It reads no Minecraft JAR, class,
resource, or world and grants no execution authority.

**This is a hypothetical generated trig-table pattern, not measured genuine
inputs beyond +0; next parent original replay decides.** The 65,536 inputs below
are deterministic generated probes, not a claim about what the unmodified
server passes to `Math.sin`. Only the already-established genuine `+0` input is
known at this point; the parent must replay the unchanged original and decide
whether any generated pattern is relevant.

## Generated Java 8 oracle

`src/MathSinOracle.java` is a dependency-free Java 8 `strictfp` program. For
`i = 0..65535` it evaluates the specified Java expression, in order:

```java
(double) i * 6.283185307179586 / 65536
```

For each `x`, the fixture records raw IEEE-754 bits for `x`, `Math.sin(x)`, and
`(float) Math.sin(x)`. There are also 23 explicitly raw-bit-selected edge
inputs: both zero signs, subnormal/normal and finite extremes, neighbors around
binary64 pi/2, pi and 2*pi, signed infinities, and signed quiet/signaling NaNs.
The TSV is ASCII with LF line endings. It records the host JDK's actual results;
`jdk8-environment.txt` identifies the Java and compiler used for this run.

Reproduce using an installed JDK 8:

```sh
JAVA8_HOME=/path/to/jdk8 ./run-java8.sh
```

Default output is `results/samples.tsv`, with generation summary, JDK evidence,
the Q120 exploration summary, and `SHA256SUMS`. The checked-in run used
OpenJDK `1.8.0_504` on Linux amd64. The script compiles only this source into a
temporary directory and removes it on exit. It does not rely on or invoke the
project build.

## Test-only Q120 exploration

`tools/explore_q120.py` uses only Python's standard library, exact integer
arithmetic, `Fraction`, and a finite `Decimal` pi constant. It reads the exact
binary64 inputs from the Java fixture, range-reduces them to `[-pi, pi]`, and
uses a Q120 fixed-point Taylor recurrence through the `x^61` term. It reports
exact counts of output-bit mismatches versus this finite-precision
approximation for both binary64 and subsequent binary32 casts. The JSON also
contains a digest of each complete mismatch list; rerunning the script gives
all exact per-index results from the pinned fixture. This is an exploratory
approximation, **not** a correctly-rounded sine implementation or evidence for
an execution-path replacement. It is never called from guest/EVM code and does
not use host `math.sin`.

The sample set, method and recorded hashes are reproducible evidence only. No
result here shows that the original program has a trig table, uses this input
grid, or can be modeled by a table or polynomial. Preserve this separation when
using or extending the evidence.
