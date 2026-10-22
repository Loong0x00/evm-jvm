# Bounded Java 8 regex anchors/plus and Matcher.matches (P41)

## Scope and authority

This task starts from the hash-verified source-only P41 snapshot documented in `../regex-anchor-plus-source-base-p41/source-manifest.json` (verification recorded in `results/source-baseline.txt`). Only this task directory may receive outputs. No original Minecraft input or parent evidence is used; the caller pattern is motivation only. No interpreter/native/heap/checkpoint/quota change is planned.

## Intended admitted grammar

Retain the existing PAT1 fixed-width literal/class program and its behavior. Extend compilation for optional `^` and `$` anchors and one-or-more on a single atom, using eager private `int[]` program words. The new counted form is a single literal or character class atom, optionally followed by `+`, with optional leading `^` and trailing `$`; inline ASCII `(?i)` remains supported. Other existing fixed-width literal/class sequences remain admitted. Quantified sequences, groups, alternation, dot, other quantifiers/flags, intersections/nested classes, and surrogate-bearing pattern/input are explicit profile refusals unless the pre-existing syntax path classifies malformed syntax as PatternSyntaxException. No host regex or lookup table.

Anchors are evaluated by the guest matcher. `$` must recognize Java 8's final line terminator boundary (LF, CR, CRLF, NEL, LS, PS), while `Matcher.matches()` still requires the complete input region. Fixed and quantified programs use leftmost, non-overlapping, greedy matching for replacement; `matches()` performs a whole-region match. Existing replaceAll replacement parsing and no-match identity behavior remain intact.

## Invariants / tests

- Preserve P41 runtime engine semantics, ABI, storage, bootstrap count, operational-native count, limits, and checkpoint wire format; only the Pattern and Matcher image contents are intended to change.
- Compile the frozen four Java sources at baseline first and compare P41 Pattern/Matcher/PSE/String images before editing.
- Generated Java 8 oracle-only tests cover distinct literal/class/range/negated-class patterns, anchors, plus min-one and greedy behavior, ASCII case-folding, replacement and `$0`, matches versus replaceAll, final terminators, nulls, malformed versus explicitly refused valid syntax, and surrogate refusal. Run small q1/q7 witnesses and a broader q4096/q65536 EVM matrix including distinct-process checkpoint reopen; retain failures.
- Reconstruct all 105 image leaves and ordered root, build fresh pinned Solidity artifacts and compare ABI/storage/source deltas. Parent alone performs any original-input replay.

## Status

Historical P41 results remain in `RESULTS.md`. P42 generated-review fixes and exact evidence are in `P42_REVIEW_FIX.md` and `p42-generated-receipts.json`. The fresh build changes only Pattern/Matcher bootstrap leaves 101/103, preserves all other 103 leaves, ABI/storage/native count and quotas, and refreshes coordinator/driver codehash authentication. Focused q1/q7/q4096/q65536 guest worlds match machine/VFS roots and pass fresh-process reopen checks; valid quantified-anchor and mutable-surrogate cases raw-refuse atomically. Build tooling writes only to unique fresh paths. P42 remains unaccepted; the earlier P41 q65536 budget history is unchanged, and no original input was accessed or replayed.
