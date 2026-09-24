# Generated-only OpenJDK 8 `Math.cos` numerical preflight

Standalone host-oracle evidence plus a test-only Q120 integer cosine experiment.
It changes no Solidity, bootstrap, guest/runtime, or original Minecraft
JAR/classes/resources/world; it reads no original artifacts and no sibling
worktree, uses no network, and makes no Minecraft progress claim. It is not an
execution-path implementation and supplies no table/output injection.

Only the first genuine original argument is currently known: `+0.0` at
`Math.cos(D)D`, original PC 299. Every other row here—including the dense grid—
is hypothetical/generated test data, not an assertion about subsequent original
inputs.

## Reproduce

Requires Python 3 and an installed OpenJDK 8. From the repository root:

```sh
./evidence/java-evm/minecraft-entry/math-cos-independent-oracle/run-java8.sh
```

Optionally set `JAVA8_HOME` to a JDK 8 installation. The script compiles only
`src/MathCosJava8Oracle.java` to a temporary directory, emits the Java fixture,
runs the Python integer model, and refreshes `SHA256SUMS`. The recorded run uses
OpenJDK `1.8.0_504` on Linux amd64. No project build or external dependency is
used.

## Fixture and refusal policy

`results/java8-oracle.tsv` contains raw input and result bits. Supported finite
inputs satisfy `|x| <= 0x401921fb54442d18` (the task-pinned binary64 bound);
controls outside it and nonfinite values are `REFUSE` rows with no call to
`Math.cos` and no output. Supported rows record `Math.cos(x)` and the raw bits of
its subsequent `(float)` cast. Input cases include:

* `x=(double)i*6.283185307179586/65536`, `i=0..65535` (a hypothetical grid);
* both zero signs, all `±k/256` for `1<=k<=1608`, and 4,096 seeded random
  magnitudes with both signs;
* raw-bit neighborhoods around binary64 pi/2, pi and 2*pi; tiny powers,
  subnormal/normal boundaries, and values around 2^-27;
* signed infinities, quiet/signaling NaNs, finite values just outside the bound,
  and larger finite values as refusal-only controls.

Rows are deduplicated by raw input bits while retaining all category labels.
The Java oracle calls `Math.cos` only after enforcing the finite raw-bit domain.

## Independent Q120 model

`tools/q120_cos.py` uses Python standard-library **integer arithmetic only**
for the cosine model; it does not call host `sin`, `cos`, `libm`, or use
floating-point polynomial arithmetic. It decodes input binary64 bits exactly,
uses the supplied nearest-even `piQ=4175892906503776358826876457663557747`,
reduces by nearest-even multiples of `2*piQ`, evaluates the alternating Taylor
recurrence through `n=30` (the `x^60` term), and rounds Q120 output to binary64
and then binary32 with explicit nearest-even integer conversions. For
`|x|<=2^-27`, including either zero sign, it returns +1 using the bound
`1-cos(x) <= x^2/2 <= 2^-55`, strictly below the half-ULP threshold below 1.
Refusal rows never enter the model.

After the n=30 term, the alternating-series remainder is at most
`pi^62/62! < (22/7)^62/62!`; the generated summary records its exact rational
upper bound and strict power-of-two bound. This truncation bound does **not**
bound all fixed-point recurrence/input-reduction errors. The summary records
observed intermediate bit lengths and product bounds for this finite generated
sample only, raw-bit double/float mismatches, maximum ULP distance and witness,
positive-grid monotonicity counts, and even-symmetry checks. `mismatches.tsv`
contains every row with a binary64 or float-cast mismatch.

Recorded OpenJDK 1.8.0_504 results: 77,517 supported rows and 74 refusal
controls; the Q120 output is at most **1 ULP** from Java 8, with 2,206 raw
double mismatches (all necessarily 1 ULP) and zero float-cast mismatches. The
65,536-point positive grid has zero sampled monotonicity violations for either
Java 8 or Q120 on both sides of the pi split. Of 5,992 available signed input
pairs, Java 8 and Q120 both have zero raw-bit symmetry mismatches. The largest
observed cosine-model intermediate is 246 bits; the largest fixed-point
multiplication is 246 bits (strictly below 2^255). The n=30 truncation bound is `< 2^-181` (fixed-point
rounding/reduction error is not covered by this tail bound).

## Interpretation limits

The exact numerical results are in `results/q120-summary.json`; they are not
assumed in advance. Java 8 `Math.cos` is the generated-input reference, but
Java's contract permits semi-monotonic results rather than universal
correct-rounding. The grid monotonicity check is sampled (split at the nearest
binary64 pi), not a proof over all reals or representable inputs. Even an exact
match on this finite set would not prove global accuracy, subsequent genuine
Minecraft inputs, an execution-path replacement, world startup, EULA acceptance,
or `Done`.
