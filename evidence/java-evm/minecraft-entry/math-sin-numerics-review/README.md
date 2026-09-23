# Test-only bounded `Math.sin` numerical controls

This standalone evidence directory contains generated-only controls for the
Q120 two-step Taylor candidate being assessed separately. It does **not** change
or invoke guest/EVM code, Solidity, bootstrap images, runtime code, the active
`math-sin-bounded` stage, or the existing independent oracle. It reads no
Minecraft JAR, class, resource, world, network, or original program input. The
only prior fixture read is the already-checked-in hypothetical 65,536-row grid
at `../math-sin-independent-oracle/results/samples.tsv`; its SHA256 is pinned in
the checker. This grid remains generated test data, not a claim about the
unchanged server's inputs. No result here grants execution-path authority.

## Reproduction

Requires Python 3 and a JDK 8. By default the script selects
`/usr/lib/jvm/java-8-openjdk`; override it without changing global settings:

```sh
JAVA8_HOME=/path/to/jdk8 ./run-controls.sh
```

The Java 8 program is compiled in a disposable temporary directory and computes
`Math.sin(double)` and its Java `float` cast directly from raw input bits. Python
independently constructs a deterministic test-only input list, evaluates the
Q120 candidate with integer bit-field conversion and exact nearest-even integer
division, checks the old grid, and records full raw-bit comparisons. All durable
outputs are under `results/`; `results/SHA256SUMS` covers scripts and outputs.
The runner never writes to the older oracle directory.

The generated input set contains signed zeros; the already-measured raw
argument `0x3f1921fb54442d18` as an explicitly labeled control (not replayed
against the original); positive/negative subnormal and normal edges; neighbors
around the `2^-27` tiny-input cutoff, π/2, π and the `2π` input bound; endpoint
and other finite boundaries; and 32,768 signed SplitMix64/rejection-sampled
finite binary64 patterns with raw magnitude at most
`0x401921fb54442d18` (`6.283185307179586`). Every sample is finite and in that
inclusive domain. `generated/sample-comparison.tsv` preserves every sample,
JDK8 result, Q120 result, ULP distance, float-cast result, and exact-match flag.

## Candidate arithmetic and interpretation

The checker deliberately implements the **two-step** recurrence, not the
combined `term*x*x` recurrence in the older exploratory script:

```text
Q = 2^120
xq = nearestEven(exact_binary64(x) * Q)
reduce xq to [-piQ, piQ] with one +/- 2*piQ adjustment
x2 = nearestEven(xq*xq / Q)
term = xq; sum = xq
for n = 1..30:
    term = nearestEven(-term*x2 / (Q*(2*n)*(2*n+1)))
    sum += term
```

The π integer is `4175892906503776358826876457663557747`, independently checked
as nearest-even `π*2^120`. The final Q120 integer is converted to binary64 by an
explicit integer significand/exponent rounding routine. For raw magnitudes at
most `2^-27`, the test candidate preserves the input bits: the analytic bound
`|sin(x)-x| <= |x|^3/6` is strictly less than half a binary64 spacing over this
interval (including subnormals). This identity shortcut is test-candidate logic,
not a claim that Java 8's specification forces a particular raw result; the
sampled JDK8 oracle results are recorded separately.

The existing 65,536-row generated grid is required to satisfy maximum binary64
ULP distance at most 1 and exact binary32-cast equality; the checker fails if
either condition is violated. Exact mismatch counts, mismatch-row digest, ULP
maximum/example, and the maximum observed signed multiplication bit length are
in `results/grid/grid-summary.json`; exact mismatching rows are in
`results/grid/grid-mismatches.tsv`. The second edge/random sample suite reports
exact binary64 and float-cast mismatch counts by category, maximum ULP distance,
and every comparison row. Near π/2, π and 2π, tiny differences and reduction
choices can change raw output bits. Java 8 `Math.sin` is not specified to be
universally correctly rounded; these finite comparisons are empirical only.

## Bounded overflow analysis (not a correctness proof)

`results/overflow-analysis.json` records both measured maximum product bit
lengths and a conservative algebraic bound, conditional on the finite input
domain and specified nearest-Q120 reduction. The reduced magnitude is bounded
by `(13/4)Q`; hence `x2 < 11Q`. The first recurrence term is below `7Q`, and
subsequent term magnitudes remain below `7Q` since later ratios are at most
`11/20`, with at most one-half Q-unit rounding per step. Therefore
`|term*x2| < 77Q^2 < 2^247`, below signed int256 maximum `2^255-1`; the initial
square is below `2^244`, the sum is below `2^128`, and the largest denominator
is below `2^132`. This addresses intermediate magnitude only. It does not prove
truncation/rounding accuracy or universal agreement with Java `Math.sin`; no
universal correctness claim is made from these tests.

No original-JAR/class/resource/world inputs, host execution fallback, host math
table, or execution-path precomputed result is present here. These scripts and
results are numerical controls only.
