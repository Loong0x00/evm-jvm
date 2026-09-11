# Parent bridge preflight replay — NOT production acceptance

See JAVA_EVM_MC_CLASS_BRIDGE_PARENT_PREFLIGHT.md. Original worker e3f45ec22 and
parent corrected copy remain distinct. No official JAR/classes handled here.
Generated Java fixture manipulation/oracles are TEST-only, never a host loader.

- baseline* independently rebuild/replay exact worker artifact cfdb6298...38657.
- padded_fixtures.py constructs valid ignored-class-attribute fixtures of exact
  4096,4097,8193,65536,65537B. Java8 returns BridgeAlpha(7)=76 for all five.
- single-read-failure*: old wrapper only executes4096;4097/8193/65536 bubble genuine
  DI0Error10 because a SINGLE read violates4096. Strict exit1 preserved.
- ClassBridge.sol/compile.js/PagedBridge.artifact.json are parent DISPOSABLE copies:
  allocate<=65536 bytes, EVM STATICCALL fragments<=4096, length-check and MCOPY. No
  host class bytes in execution input; exact accepted VFS0a engine unchanged.
- sizes.go.txt is original size probe. traced-base.go.txt/traced-sizes.go.txt add
  diagnostic EVM call-frame observation of DI0 read sizes; no trace recovery.
  The base remains the labeled reflection-based disposable world, not production.
- paged-sizes*: all four legal sizes execute76/181 instructions,65537 still rejects8.
 65536 direct and26q7 slices have the same terminal machine root/counters/result.
  Max direct call4698971gas; actual read shapes1/2/3/16 fragments, never>4096.
- paged-original*: original3 result chains and6 refusals pass on corrected artifact.
- reproduce.sh reconstructs into NEW ignored output, checks the original failed
  boundary, the corrected paging proof, Java8 oracle and original results. Fresh
  final run6.751s/320335872B sampled groupRSS,20min4GiB watchdog,exit0/no limit.
  An initial reproduction script incorrectly expected bare76 while Oracle prints
  BridgeAlpha(7)=76; its failed assertion is preserved in oracle-format-failure*.
  No semantic result changed to make it pass.

Corrected artifact SHA256
6f5525022d299dd2ad3403101f353bdfadbf7c9f1fd635dfc653207908c44db2;
runtime3978B SHAaa3f663e67279bc02bae4ba7e3afd0bdfa538fd91d1754378bd591e7859e5897;
init4021B SHA2b84525276ce3804bb8664537bc2ed7a15da24d5d2acc4732585316208391e7f;
source900d3142cfb02cab56a7ed1cd07df14eba040366fc55e5af16dfdfaf83c87d99.

From repository root, use NEW paths (do not overwrite this archive):

```
python3 evidence/java-evm/watchdog.py build/java-diff-NEW.log build/java-diff-NEW-watchdog.json \
 bash evidence/java-evm/class-bridge/parent-e3f45ec22/reproduce.sh build/java-diff-class-bridge-NEW
```

Reflection only joins a private test StateDB and installs exact accepted LOCAL
engine bytes; there is no legal production shared-world transport yet. Bridge Java
calls here are not per-call committed/reloaded. Head-absence tests after host
snapshot restoration do not establish independent post-write rollback. Production
must fix the class package per instance instead of relying on driver-only binding
comparison. Next shared-world preflight must remove private-session attachment and
measure real disk/new-process checkpoint continuation before any production freeze.
