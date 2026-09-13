# Parent original Properties gas measurement

**Read-only measurement, not a semantic optimization or startup acceptance.**
Worker c10a13be7/4d3f37402 integrated locally as599614087/88b158fe2. Parent evidence:
`evidence/java-evm/minecraft-entry/parent-4d3f37402/`.

Parent independently rebuilt compiler metadata from unchanged Solidity with the
pinned compiler/options. Complete AST/source-map/IR metadata equals the worker
capture, and emitted runtime equals the already parent-verified321590-byte engine,
Keccak `eb4c959c4893d83ef2a20918693f1ab499d812845a54b9377eba3615a8da1be7`.
No engine/ABI/profile/limit change. Source is ASCII, so source-map byte offsets
and the mapping script's character offsets agree for this exact source.

Fresh generated ON/OFF controls pass for small construction q7 and large direct
reserve refusal. Parent then applies the same observer to the actual paused
original20 epoch249 checkpoint, through public ResumeMain(q1), not raw-class input
or recovered failed state. Observer OFF and ON both return exactly:

* gas **73494750**, raw `LC0ControlError(7)`;
* same pre/post EVM root
  `cab02d0edfa25399fb5e51113cad2003c4f72b1ad8ccd52dfca61840e0c5c600`;
* byte-identical Head and prior11359B checkpoint (SHA affcf10ae1a90714a60255dc1b13475e62026d412dd38b1993e802b36528d2fe).

## Original guard differs from generated guard

The original terminal PC is **5892 REVERT**, mapped to **_commit, line838:49**:
`if (gasleft() <= COMMIT_RESERVE) revert LC0ControlError(7);`
It is the checkpoint-commit entry reserve check, not the _execute guard identified
in the worker's generated control (PC115770/line3816). No intermediate failed-call
Java state is recovered or credited as committed Properties allocation.

Original engine measurement:

* **14800198** opcodes, **70300373** exclusive opcode gas; no engine child
  forwarded gas. Difference from total call gas3194377.
* max engine memory/free pointer **2984096B**;5844 pointer changes.
* PC counts/costs and mapped-function cost totals independently reconcile.
* largest named buckets: `_findClass`2969404, `_u2`2737844,
  _validInternalName2482203, _descriptorType2051211.
* contract-wide/compiler source bucket43736938 is not one identified function.
  The observed single-engine memory maximum implies17264372 gas under the EVM
  expansion formula; this is already included in opcode costs, not additive.

Limits/caveats: the observer does not retain raw memory/stack/calldata/class/pages.
Its growth-byte counter omits the initial96B; it gives pointer changes/max, not
an allocation-size histogram. Nested forwarded caps are not expenditure, and
aggregate child-used gas is not an exclusive additional total. No cost-category
claim beyond these observations. No full Session audit or optimization accepted.

Whole independent metadata build + generated ON/OFF + original ON/OFF + mapping:
**206.106481s**, sampled process-group peak **970489856B**, exit0. Absolute fresh
ignored TMPDIR and inherited process groups preserve the20min/4GiB monitor.
Only safe aggregate diagnostics and prior mutable checkpoint metadata are archived,
not original JAR/class/resource-page or LevelDB payloads.

## LOCAL budget policy clarification

The user asked whether limits can be relaxed when mainnet is not a goal. **Yes**:
100M is this experiment's budget, not an EVM hard limit. Parent proposed a separate
LOCAL-only1B call budget with time/memory protections; raising a ceiling does not
force that much actual gas usage, and local simulation does not pay real ETH.
That was a proposal, not an executed amendment: this measurement still uses
100M gas,25M reserve and all prior limits. No push/new budget change occurred.
A larger budget would remove this particular reserve threshold but does not
establish that missing Java APIs, physical frame limits or startup are solved.
Current original frontier remains epoch249/1683J/10I, no main-body/world/Done.
