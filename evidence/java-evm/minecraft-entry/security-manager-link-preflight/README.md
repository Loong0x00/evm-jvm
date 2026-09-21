# Generated image94 `SecurityManager` link stage

This generated-only stage implements `JAVA_EVM_MC_SECURITY_MANAGER_LINK_PREPARATION.md` from `classcount50-byte324338-preflight`. It appends exactly one bootstrap image, `java/lang/SecurityManager`, at ordered leaf94. Its only member is public `<init>()V`, chaining directly to `Object.<init>()V`.

The prior 93 leaves, their order, raw50/324338 limits, native13, String-local binding10, exception kinds14, frame/checkpoint/Head bounds, compiler settings, and all retained generated cases remain pinned. The checkpoint diagnostic bound alone advances `143→144`. The image is bootstrap-owned; a raw replacement is refused before guest execution. The source verifier recompiles the generated 140-byte Java-8 image and checks that no other image leaf changes.

The fresh root is `8d2893be300e29b3d31073f82267880b1c50c428a83d86113eafc884fa340b7d`. To retain the fixed 393216-byte LOCAL runtime cap, only image94 uses its independently checked leaf commitment; all pre-existing leaf material remains inherited exactly. Rebuilt engine size is `393007 / 393216` bytes (209-byte headroom); coordinator is 5392 bytes.

Focused q1/q7/direct/reopen construction, Object/checkcast type-link, dormant-image, raw-replacement, and representative omitted-API controls are included alongside the retained generated suite. No permission checks, class context, policy, installation, `System` security state mutation, or host security behavior is included or claimed.

No original artifact/JAR/class/resource, provider/factory construction, world, or Done input is read or claimed. Parent owns genuine replay.

## Reproduction

From repository root, using fresh ignored `build/` paths:

```sh
python3 evidence/java-evm/minecraft-entry/security-manager-link-preflight/tools/verify_source.py --built evidence/java-evm/minecraft-entry/security-manager-link-preflight/build-pins.json
python3 evidence/java-evm/minecraft-entry/security-manager-link-preflight/tools/build.py build/java-diff-mc-security-manager-link-build-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/security-manager-link-preflight/tools/generate_fixtures.py build/java-diff-mc-security-manager-link-fixtures-repro-LOCAL
python3 evidence/java-evm/minecraft-entry/security-manager-link-preflight/tools/gate.py build/java-diff-mc-security-manager-link-build-repro-LOCAL build/java-diff-mc-security-manager-link-fixtures-repro-LOCAL build/java-diff-mc-security-manager-link-gate-repro-LOCAL
```
