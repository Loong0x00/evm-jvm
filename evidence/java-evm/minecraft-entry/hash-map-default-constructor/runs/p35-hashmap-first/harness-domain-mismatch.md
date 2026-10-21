# Preserved harness-only failure: coordinator package-domain mismatch

The first `p35-hashmap-first` attempt passed the full direct generated-engine gate
and fresh-process reopen, then the positive coordinator `CREATE` reverted with
`MR0Error(16)` (asserted package-root mismatch). Its `failed-run.json` preserves
all command arguments, runtime pins, budgets, exact revert bytes, and the failed
coordinator call; no engine execution/refusal was implicated.

Cause: the inherited Go coordinator route helper used the older
`MC-RANDOM-CLASS-P28/{package,class}/v1` fixture domains, while the exact P34
coordinator Solidity source authenticates `MC-CHECKPOINT-2M-P34/{package,class}/v1`.
The EVM correctly rejected the route's inconsistent asserted root. Only those two
Go test-helper domain strings were corrected. The next fresh full run,
`p35-hashmap-domain-fix1`, passes direct, reopen, and coordinator gates with the
engine and coordinator artifact pins unchanged.
