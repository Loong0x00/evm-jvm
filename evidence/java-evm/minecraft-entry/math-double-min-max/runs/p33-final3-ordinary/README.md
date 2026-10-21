# Generated-only Math double min/max gate

Reproduce from repository root with:

```sh
python3 evidence/java-evm/minecraft-entry/math-double-min-max/tools/run_gate.py p33-final3-ordinary
```

This archived run passed the ordinary 1,000,000,000-per-call gas / 1,200-second
test-only wall budgets without expansion. It contains the exact Java 8 fixture
and read-only oracle manifest, engine/coordinator pins, q1/q7/q65536/q4096
schedules, fresh-process q1 edge checkpoint reopen, coordinator exact-raw150
route, opaque terminal checkpoints, command logs, and source hashes. It does not
contain original Minecraft execution data and does not claim parent P33 review
or original77 replay acceptance.
