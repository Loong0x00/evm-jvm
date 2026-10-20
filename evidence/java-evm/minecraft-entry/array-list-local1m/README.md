# LOCAL1M ArrayList(int) candidate and generated EVM tests

This remains the pinned minimal b6a8ebe13 append under the user-authorized LOCAL1M runtime ceiling. The generated-only ArrayList EVM tests now pass, including a fresh paired coordinator and both direct raw-class and canonical AS0/ZI0/DI0 package transports. This is still candidate evidence pending parent profile review; it is not an accepted profile or an original Minecraft run.

- Main generated EVM report: `runs/final-3e87b6e07-3/README.md`
- Reproduce with `python3 evidence/java-evm/minecraft-entry/array-list-local1m/tools/run_gate.py <new-run-id>` from the repository root.
- A corrected harness-only false-positive attempt is retained at `runs/final-3e87b6e07-1/README.md`; it is not a candidate failure.
- Exact source/artifact pins and behavior summary: `pins.json`, `source-and-build-record.json`
- Engine runtime: 394435 bytes, SHA-256 `61b71a4377733891a4a91ebff2a1765b2c96ecce268e69e9ec7d8ed0320a8df8`
- Paired coordinator runtime: 5394 bytes, Keccak `99a642d08d254eb5083314f61e73ee429cc5ac3634bd8c8348a195b0d72001e3`
- Existing LOCAL384 candidate/failures remain preserved separately.

The engine runtime is executed through explicit LOCAL preinstalled-code Call, not ordinary CREATE/EIP-170 deployment. No official Minecraft JAR/class/resource/world/checkpoint was read or executed; no EULA/config/listener/Done claim is made. Underlying EVM/core/state/consensus, bootstrap semantics, and all existing quotas remain unchanged.
