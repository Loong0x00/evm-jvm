# Parent System.getSecurityManager preflight

**In progress; generated worker result is not acceptance.** Worker f45ab41ed /
ed13f2126 /2293e298e integrated locally as the three commits immediately after
de8bdadfa. Parent evidence/recipes:
`evidence/java-evm/minecraft-entry/parent-2293e298e/`.

The narrow candidate recompiles the owned System class with one private nullable
SecurityManager reference and exact public static getter. Default guest static
state is null. It retains arraycopy unchanged and has no setter, SecurityManager
class, permission framework, ClassLoader, System properties or resource-search
fallback. A null reference result does not require a concrete class object.

Parent `rebuild.py` independently compiles the System guest source, asserts exact
338B/SHA256 image, mechanically preserves the other47 bootstrap bytes, rebuilds
Solidity from parent-c24d374bc sources, and compares complete artifacts with the
candidate. It separately derives the driver from the actually executed, explicitly
user-authorized LOCAL1B source. No old runtime checkpoint is reused because code
identity changes.

Candidate pins pending independent gate:

* LOCAL initial-state engine `0x4d43534543555249545947455454455200000001`,
  domain `MC-SECURITY-GETTER-PREFLIGHT1`;
* engine322301B, SHA256
  `4a8aafbfafef9fed3c3fd3106d99b9819a40ecc2eccfe40e234efa448dc038f9`,
  Keccak `74609271d2d333b617e12d0c2ddeae2574b7812fc72f719453614acb3cc081ae`;
* ordinary-CREATE coordinator3547B, Keccak
  `113bcbc2b3512af2cbddc90379dbc8cacfb64f7df50ef7ec8f89e1bdfe8ed59a`.

`run.sh` is under one20min/4GiB process-group watchdog. It removes the worker
runner's nested process sessions before running fresh generated q1/q7/direct,
reopen and canonical receipts. If these pass, parent alone starts a NEW original21
world through EVM AS0/ZI0/DI0 under authorized1B,30s/25M reserve and stops at the
next actual blocker. The actual runtime MAX_FRAMES remains128; no old diagnostic16
claim. All24/262144, CP/Code/heap/VFS/checkpoint/Head/engine limits unchanged.
No original payload is archived; no accepted/core/ABI/Makefile/push change.
