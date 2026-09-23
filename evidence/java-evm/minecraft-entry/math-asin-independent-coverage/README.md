# Generated-only adversarial `Math.asin(double)` coverage

This directory is an independent, reproducible test-only numerical experiment
for the measured `Math.asin(D)D` candidate. It neither edits nor invokes
Solidity, bootstrap images, guest/runtime code, the active bounded-asin stage,
sibling worktrees, Minecraft classes/resources/world, or the original server
JAR. The only authenticated original argument currently known is binary64
`+0.0`; every input in this directory is a generated control. No oracle result
is injected into any execution path, and these results make no claim about
actual Minecraft behavior beyond that already authenticated `+0.0` argument.

`AsinCoverageJava8Oracle` alone invokes `java.lang.Math.asin`, and does so only
for generated finite inputs with `|x|<=1` on OpenJDK 8. The independent
`Q120AsinCoverageProbe` is integer-Q120 arithmetic plus ordinary exact
integer/float-bit bookkeeping; it does not call host transcendental math. Both
are standalone host-side tests, not guest or EVM execution code.

## Reproduction

Requires an installed JDK 8. From the repository root:

```sh
./evidence/java-evm/minecraft-entry/math-asin-independent-coverage/run-java8.sh
```

Or set `JAVA8_HOME` to another JDK 8. The script compiles only the two local
sources into a disposable temporary directory, generates the oracle samples,
runs all three integer controls, and refreshes hashes in `results/SHA256SUMS`.
It uses no project build, network, or external dependency. Oracle bits can vary
between OpenJDK 8 builds; environment/version and output hashes are recorded.

## Generated controls and measurements

The deduplicated input set contains:

* the complete `k/65535.0`, `k=0..65535` grid, with both signs (including
  distinct `+0.0` and `-0.0`);
* 257 adjacent binary64 values inward from each signed endpoint, geometric
  approaches to `+/-1`, and neighborhoods around `|x|=1/2` and the `2^-27`
  tiny-input cutoff;
* signed subnormal/normal/zero edge vectors and 4,096 deterministic uniform
  plus 4,096 exponent-stratified finite magnitudes, each with a negative
  mirror;
* finite out-of-range, infinity, and NaN refusal controls. `Math.asin` is not
  called for these rows and no result is fabricated.

For each supported input the integer probe compares the raw binary64 result
and the raw binary32 bits obtained by casting that result against the OpenJDK 8
oracle. It records all mismatches in `results/mismatches.tsv`, per-iteration
counts/max ULP/worst input, sampled binary64 and float monotonicity violations,
and per-operation plus maximum absolute intermediate bit lengths in
`results/q120-summary.json`. It also checks 4,096 random integer square-root
floor inequalities and 4,110 exact-rational nearest-even Q120-to-binary64
conversions.

The three controls use the same nearest-even Q120 recurrence
`t[n] = t[n-1]*x^2*(2n-1)^2/(2n*(2n+1))`, with integer floor square root and a
Q120 `pi/2` scalar; each result snapshots the recurrence after `n=N` for
`N=32,64,128` (initial term `t[0]` plus N updates). Values above `1/2` use
`asin(x)=pi/2-2*asin(sqrt((1-x)/2))`; signed outputs are mirrored exactly.
For `|x|<=2^-27`, the candidate preserves input bits under the usual
`0<=asin(x)-x<=x^3/(6(1-x^2))` half-ULP bound. All tracked algorithm
intermediates are checked to have absolute value below `2^255`.

For the positive series on `0<=z<=1/2`, coefficients are at most one, so after
including terms through `t[N]` the omitted positive tail is bounded by the
geometric sum

```
Σ(n=N+1..∞) z^(2n+1) <= (1/2)^(2N+3)/(1-(1/2)^2)
                         = 1/(3*2^(2N+1)).
```

The endpoint-reduced result multiplies this series by two, so its corresponding
series-tail contribution is at most `1/(3*2^(2N))`. Explicitly:

| N | series omitted tail | endpoint-reduced result contribution |
|---:|---:|---:|
| 32 | `1/(3*2^65)` | `1/(3*2^64)` |
| 64 | `1/(3*2^129)` | `1/(3*2^128)` |
| 128 | `1/(3*2^257)` | `1/(3*2^256)` |

These analytic bounds cover only the omitted exact positive-series terms. They
do not bound Q120 rounding, sqrt truncation, pi constant, or OpenJDK error, and
are not a universal correctness proof.

## Results and limits

On the recorded OpenJDK `1.8.0_504` environment, the set has 148,595 unique
rows (148,584 supported and 11 refusal controls). Each of N=32,64,128 has
8,384 raw-double mismatches, all at most 1 ULP; all have zero float-cast-bit
mismatches, zero sampled double/float monotonicity violations, and a maximum
tracked algorithm intermediate width of 239 bits. The detailed mismatch list
contains 25,152 variant/input rows. These finite observations are measurements,
not acceptance criteria or a universal correctness claim.

See `results/oracle-summary.txt`, `results/run-summary.txt`,
`results/q120-summary.json`, the full oracle `results/samples.tsv`, and every
reported mismatch in `results/mismatches.tsv`. `results/SHA256SUMS` covers the
standalone sources, reproduction script, reports, samples, and mismatch list.
The earlier `../math-asin-independent-oracle/` evidence remains read-only and
is not an input dependency.

Comparison with OpenJDK 8 is a finite generated test, not a proof of exact or
semi-monotonic behavior for every binary64 value. Sampled monotonicity is only
for the recorded set. This standalone experiment does not measure EVM gas,
atomicity, native binding semantics, runtime acceptance, original Minecraft
values after `+0.0`, or Minecraft readiness.
