# M1: Java interpreter genuinely inside EVM

## User correction / current priority
The user wants the actual JVM-inside-EVM route, not host-side Java→EVM AOT translation. Their exact request: “嗯对,对就是应该全都跑在EVM上,用5.6solhigh模型跑吧.” Resolved installed model: `openai-codex/gpt-5.6-sol`, reasoning `high`. One implementation worker; parent independently verifies.

Keep the previous smallest-goal and agent-friendly Git requirements. Do not implement more Java features yet. Preserve the verified M0 AOT experiment (commit `0376480`, implementation `a9b439b`) as a clearly labeled baseline, not the primary claimed JVM-in-EVM path.

## Non-negotiable execution boundary
```
BUILD TIME (host): javac → Add.class; compile interpreter implementation → EVM runtime bytecode
RUN TIME: host packs unchanged raw Add.class + entry name + int args into calldata
          → geth EVM executes the SAME generic interpreter runtime bytecode
          → IN EVM: classfile parsing → method/Code lookup → Java bytecode dispatch
          → IN EVM: iload / iadd / ireturn → EVM returns signed int result
HOST: decode result and display measured gas
```
- Build-time compilation of Java input and the interpreter is allowed. No compiler toolchain bootstrapping or Java source compiler inside EVM in this milestone.
- Host may ABI-encode bytes/name/arguments, but MUST NOT parse Java classfiles, extract Code, predecode JVM instructions, select Java methods, translate Java to EVM, specialize interpreter to this class, or calculate the Java answer on the actual execution path.
- No native JVM precompile, custom host-Java opcode, Go JVM evaluator, subprocess Java execution backend, or hardcoded answer.
- The same interpreter EVM bytecode must accept different original classfiles AND runtime arguments without recompiling the interpreter. This is an interpreter for a minimal JVM subset, not full Java SE.

## Minimal feature scope
- Actual `javac --release 8` classfiles, including constant-pool scanning, method name/descriptor/access checks and Code lookup performed inside EVM.
- Selected unambiguous static method with int arguments and int return.
- Only iload (including short forms), iadd, ireturn are needed. Ignore unused constructor as an unexecuted method.
- Correct int32 wraparound and signed result handling. Explicit EVM-side errors for unsupported selected bytecodes, missing/ambiguous method, unsupported descriptor, invalid local/stack use and malformed/truncated class input; do basic bounds checks, honestly document not a full JVM verifier.
- Avoid silently claiming class initialization/synchronization/exception semantics; reject such unsupported selected-method/class initialization features where practical or clearly scope trusted inputs. Do not build a full verifier.
- Use finite configurable gas; parsing and interpreter loop gas must be counted by actual EVM execution.

## Implementation and usability
- Work only in `/home/user/evm-jvm/geth` on existing branch `java-on-evm`, a real local Git fork. No remote push/fork or global config changes. Keep VM consensus core unchanged.
- Choose the simplest maintainable in-EVM implementation (Solidity or Yul compiled to standard EVM runtime bytecode is recommended). If compiler dependencies are needed, pin them and keep package manifests/lockfiles scoped to interpreter directory; do not change global npm/tools.
- Separate build of generic interpreter artifact from executing Java inputs. Ensure reproducible artifact generation (embed checked-in runtime artifact or otherwise make CLI/tests usable with a clearly documented build step); record compiler version/settings and source-to-artifact consistency check.
- Preserve M0 API/CLI/tests in clearly labeled paths/commands. Make main `make java-demo` / `make java-test` exercise the genuine in-EVM interpreter, with explicit AOT aliases for baseline if appropriate. Keep commands simple and avoid hidden build dependencies.
- Update AGENTS.md (file map, build/demo/test, current boundary), JAVA_EVM.md (precise quickstart, actual execution gas, limitations), and this plan's status. Do not claim Minecraft or full JVM.
- Run focused checks, then create scoped local Git commit(s) using configured identity. Stage exact task paths, leave working tree clean and return hashes. This parent-authored plan is authorized for inclusion.

## Acceptance evidence
1. `Add.add(20,22)` produces 42; negative and overflowing cases match JVM.
2. Same generic interpreter runtime bytes/hash execute at least two different original Java classes: addition and identity (e.g. `return b`), plus repeated runtime arguments. No host class preprocessing.
3. Pass raw unsupported-multiply class and raw malformed/truncated class via CLI: failure occurs as EVM execution/revert, not a host Java parser error. Test insufficient gas as actual EVM out-of-gas.
4. Tests/source review demonstrate actual EVM class scanning and opcode dispatch. Use opcode tracing or similarly inspectable evidence if useful; no need for a large tracing framework.
5. Rebuild generic interpreter from checked-in source with pinned compiler and verify artifact matches; focused tests and demo work via documented commands. JVM oracle runs may be added to tests only, clearly outside execution backend.
6. Parent independently inspects host-vs-EVM boundary and reruns focused tests/demo and selected differential/error cases.

## Status
- Worker implementation complete and locally verified; parent acceptance review pending.
- Implemented as a generic Solidity 0.8.30 runtime with unchanged raw-class ABI input, in-EVM classfile/method/Code parsing and in-EVM JVM opcode dispatch. M0 remains a labeled baseline.
