# Stock-EVM S0 runtime

This directory is the frozen S0 deployment/continuation subset. It is separate
from `jvmevm/runtime` and supports only the integer opcodes and class profile in
`JAVA_EVM_STOCK_S0_PLAN.md`; it is not an M5d-a migration or a full JVM.

Build reproducible artifacts with `npm ci && npm run build`; verify checked-in
artifacts with `npm run check`. The build is pinned to solc 0.8.30, optimizer
runs 200, via-IR, Cancun, with compiler metadata disabled. Compiler inputs are
the four Solidity files only.

`ArtifactPage` returns runtime code exactly `STOP || payload`. The module parses
and predecodes that payload in EVM on every call. `VMCoordinator` pins actual
page/module code hashes and atomically commits bounded canonical checkpoints.
The configured module hash is a commitment, not proof that arbitrary supplied
code implements this interpreter; deployments must compare it to the pinned
artifact and immutable references.
