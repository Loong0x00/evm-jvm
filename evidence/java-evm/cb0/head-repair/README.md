# CB0 head/ABI repair evidence

This directory records the bounded validation repair based on `1ec057f00`.
All probes use the embedded CB0 artifact and generated in-memory transport state
only. They do not read an official JAR, parse class bytes, inflate ZIP data, or
run Java/Minecraft.

`before-validation.log` was produced with the pre-repair `head.go` and
`artifact.go`, while the newly added focused tests remained present. It shows
that the former empty runtime-Keccak placeholder, output-only ABI changes, and
a copied fixed-engine-code shape were accepted. This is a validation baseline,
not a live ownership bypass: copied-state tests only demonstrate that `Head`
refuses malformed EVM state.

`after-ordinary.log` is the 100M/30s ordinary focused run. `after-boundary.log`
is the separately labelled 1B/120s `Head` boundary call. `after-vet.log` is the
matching package vet run. The scripts do not claim a complete CB0 transport or
acceptance; coordinator ordering/pipeline behavior remains parent-owned.
