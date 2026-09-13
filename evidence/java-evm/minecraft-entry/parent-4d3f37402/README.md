# Parent original cost evidence

See JAVA_EVM_MC_PROPERTIES_COST_PARENT_PREFLIGHT.md for exact scope/results.
run.py rebuilds identical compiler metadata, replays fresh generated ON/OFF
controls, then traces only the same-code paused original q1 call. Head/checkpoint
bytes and EVM root stay unchanged. No failed state is used as an execution input.
metadata/ contains the independent unchanged-source rebuild; original-observation
is aggregate PC/cost/memory-size data, no raw EVM memory/classes/pages. The prior
checkpoint is public mutable machine state, not a class image. Source mapping
identifies original _commit rather than the worker's generated _execute guard.
The10^9 LOCAL budget is only proposed, not applied by this measurement.
