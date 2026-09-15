# Formal task 2/3 — System.err

## Comparative validity

No model winner is declared for this task. Both corrected-run streaming files were contaminated by detached processes from the earlier contradictory-task pilot after the parent killed tmux wrappers without first terminating their Pi process groups. The impossible negative TTFTs and stream durations exceeding wall time make throughput/token metrics non-comparable. The raw records and invalid pilot remain preserved rather than silently discarded.

At the outer-process level, Terra timed out at 1200.071s after committing a strong source/verifier/gate design but intentionally refusing to borrow missing dependencies from another worktree. DeepSeek exited0 at 1067.514s and ran generated gates, but its selected product changed the fixed Solidity optimizer from runs200 to runs1. Therefore neither submission was machine-eligible and no blind comparative judging was launched.

## Parent engineering recovery

The parent selected Terra commit `3b2026179` as the repair basis, fixed two generated-fixture bugs, then removed Terra's precomputed commitment size workaround after independently proving that the simpler runtime-derived design already fits with the required optimizer200. The final parent build is 392775/393216 bytes, and the complete generated gate passed with 1086 canonically verified receipts. Fresh original30 advanced to 8697J/39I and now honestly requests `java/lang/StringBuilder`.

This recovery is engineering evidence, not a retroactive model benchmark win. Formal task1 remains the valid measured Terra-vs-DeepSeek comparison.

## Parent-amended acceptance review

Three independent Sol-xhigh reviewers unanimously accepted the parent-amended implementation. Median scores were correctness9.6, architecture9.7, minimality10.0, robustness9.3, maintainability9.3, and completion9.7. One reviewer noted a low-severity residual: failed-initialization coverage uses the retained generic state-machine control rather than inducing failure inside shipped `System.<clinit>`; this does not block the strictly measured successful field-access scope.
