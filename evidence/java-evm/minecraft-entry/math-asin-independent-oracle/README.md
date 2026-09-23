# Generated-only Java 8 `Math.asin` numerical preflight

This is a standalone host numerical oracle and test-only integer-arithmetic
experiment for the proposed next measured symbol `Math.asin(D)D`. It does not
edit or invoke Solidity, bootstrap images, guest/runtime code, Minecraft, the
original server JAR/classes/resources/world, sibling worktrees, or the network.
It makes no original-program simulation or execution-path claim. `Math.asin` is
called only by the generated-input OpenJDK 8 oracle; the Q120 candidate never
calls host transcendental math and is not wired to guest execution.

The only authenticated original input currently known is `+0.0`; this
experiment treats all subsequent values as unknown. The grids, edge vectors,
and deterministic random vectors below are generated controls, not a claim
about original inputs.

## Reproduction

Requires an installed JDK 8 (default in this environment:
`/usr/lib/jvm/java-8-openjdk`, OpenJDK `1.8.0_504`). From the repository root:

```sh
./evidence/java-evm/minecraft-entry/math-asin-independent-oracle/run-java8.sh
```

Or set `JAVA8_HOME` to another JDK 8. The script compiles just the two Java
sources into a temporary directory, generates `results/samples.tsv`, runs the
independent Q120 probe, then refreshes result hashes. No project build or
external dependency is used. A different JDK 8 may legitimately produce
slightly different oracle bits; its version and resulting hashes are recorded.

`samples.tsv` contains raw binary64 inputs and, for supported rows only, raw
OpenJDK 8 `Math.asin` binary64 and subsequent binary32-cast bits. It covers:

* every `k/256`, `k=0..256`, and all negative mirrors (including both zero signs);
* 65 successive representable inputs inward from each of `+1` and `-1`, values
  around `1/2` and `2^-27`, subnormal/normal boundaries and tiny inputs;
* 4,096 deterministic random magnitudes from each of uniform and
  exponent-stratified generators, each with a negative mirror;
* refused-only controls for finite `|x|>1`, infinities, and several NaN bit
  patterns. The host oracle intentionally does **not** call `Math.asin` on
  these controls and records no fabricated result.

The exact set is deduplicated by raw input bits. `oracle-summary.txt` identifies
the JDK and the sample hash. `mismatches.tsv` contains every binary64 raw-bit
and/or float-cast mismatch; a header-only file means none. `q120-summary.json`
records the max ULP distance, worst input, support/refusal policy, sampled
monotonicity check, exact sqrt and conversion validation counts, and maximum
observed absolute signed intermediate bit lengths. `SHA256SUMS` authenticates
the reproducible sources and generated summaries/results.

The recorded OpenJDK `1.8.0_504` run has 17,066 supported rows and 11 refused
controls. The Q120 candidate has **maximum distance 1 ULP**, 472 raw binary64
mismatches (all listed; each is one ULP), zero subsequent float-cast-bit
mismatches, and zero sampled monotonicity violations. Every measured arithmetic
intermediate is below `2^255`; the largest recorded bit length is 240. This
meets the bounded `<=1 ULP` numerical target on this generated set but is not
bit-identical to OpenJDK 8 on 472 cases and does not prove the global Java
semi-monotonic/correct-rounding contract. See the exact mismatch rows and JSON
summary rather than treating the candidate as accepted runtime behavior.

## Test-only Q120 candidate explored

The candidate represents values as signed integers scaled by `Q=2^120`.
Inputs with `|x|<=2^-27` retain their original bits: for `x>=0`,
`0 <= asin(x)-x <= x^3/(6(1-x^2))`, which is strictly below half an ulp
through that cutoff, including subnormals. Signed zero is preserved. All other
supported binary64 inputs in this range are exactly representable in Q120.

For `0.5 < |x| < 1`, it forms `y=(1-|x|)/2`, computes
`floor(sqrt(y*Q^2))` with integer Newton iteration and exact floor correction,
then uses `asin(|x|)=pi/2-2*asin(sqrt(y))`. The series branch sums terms `n=0..128`
with the recurrence

```
t[n] = t[n-1] * x^2 * (2n-1)^2 / (2n*(2n+1))
```

using nearest-even integer divisions at Q120 scale. For `|x|<=1/2`, the omitted
exact positive tail after `n=128` is bounded above by
`(1/2)^259/(1-1/4) < 2^-258`; each recurrence division uses nearest-even rounding. The observed comparison
is against OpenJDK 8 and cannot isolate candidate approximation error from the
host `Math.asin` implementation. The sole scalar
constant is the nearest integer to `(pi/2)*2^120`, checked against a long
finite decimal expansion. `x=±1` maps through that constant. The final Q120
integer is converted to binary64 by integer nearest-even rounding.

The probe also independently validates the Q120-to-binary64 conversion on
named/tie cases and 4,096 deterministic integers by exact `BigDecimal`
midpoint comparisons, and checks exact floor-sqrt inequalities on 4,096
random 240-bit radicands. The candidate's finite sample is sorted by raw
numeric input order and checked for nondecreasing outputs; this checks only
those samples, not every binary64 input. Every tracked arithmetic intermediate
is guarded against `|v| >= 2^255`; `q120-summary.json` gives per-operation
maxima. These are generated numerical-preflight checks only, not a proof of a
future EVM implementation or its gas/atomicity behavior.

## Interpretation

All mismatches are reported rather than patched with outputs. A zero-mismatch
run establishes only that this bounded candidate matches this generated
OpenJDK 8 test set (and the measured intermediate-width conditions). It does
not establish correctly-rounded `asin` for every binary64 input, Java
semi-monotonicity globally, suitability for the EVM, or relevance of generated
inputs to Minecraft. No host table/oracle value is execution input.
