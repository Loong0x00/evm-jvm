# Reentrant lock generated-only source gate

Source commit: `4bcfc4ab6`. This archive contains no original Minecraft input,
world, LevelDB state, generated Solidity binary, or class/ZIP payload.

`source-verification.log` records the stripped Java 8 rebuild, exact reverse-to-COW
check, and all-75-prior-image identity. `fixture-summary.json` records only trusted
host Java 8 fixture hashes. `gate-summary.json` records fresh LOCAL384 generated
EVM worlds: lock q1/q7/q4096 (direct), durable reopen, canonical terminal root and
opaque payload equality; retained COW q1/q7/q4096/reopen/canonical equality; and raw
replacement refusal before Head/root mutation for all four appended names.

Metrics: engine 385212 bytes (under the fixed 393216-byte LOCAL384 cap), coordinator
4146 bytes; lock terminal 218 Java/2 internal steps at epochs 218/32/1 and class
count80; retained COW terminal748 Java/8 internal steps at epochs748/107/1 and
class count80. Whole generated gate: 55.417851860 seconds wall, 39.196585 seconds child user, 1.606004 seconds child system, and 66516 KiB child maximum RSS (see `gate-monitor.json`). The raw refusals used
380568, 381887, 406319 and 405220 gas, respectively.

Caveat: the retained test is focused only; COW quota/OOM and other parent-profile
reruns were not executed here. The family is deliberately a single-guest-thread
hold-counter/accessor slice, not fairness, conditions, timed/interruptible lock
acquisition, ownership transfer, contention, or unbalanced-unlock exception behavior.
