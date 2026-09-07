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
- Worker implementation committed as `11e2e888c3fd9ecf56c32a65866e150750b20295`; independent parent acceptance passed.
- Implemented as a generic Solidity 0.8.30 runtime with unchanged raw-class ABI input, in-EVM classfile/method/Code parsing and in-EVM JVM opcode dispatch. M0 remains a labeled baseline.
- Parent inspected `cmd/jvmevm` → `jvmevm.Run`: only raw file read, ABI packing, generic `runtime.Execute`, and result decoding. Solidity `interpret` and `_execute` perform class scanning and Java dispatch. No changes to `core/vm`, `javaevm`, or `cmd/javaevm` relative to M0.
- Independently reran `make java-test`, `make java-demo`, `make java-aot-test`, and `go vet ./jvmevm ./cmd/jvmevm`; all passed. Pinned source rebuild matches the 5044-byte runtime with SHA-256 `e93a3281bde126b8ea87972d75e0ac03a53d0de17fbffb6402fce9764bec2c20`.
- Demo returned 42 with 46,391 execution gas. Parent compiled an additional multi-method Probe class and compared 30 add inputs (5 edge cases and 25 seeded random pairs) against actual host JVM as test oracle: all matched with the same runtime hash.
- The same artifact also executed a separate Identity class (-123, 46,213 gas), and Probe.fifth using general `iload` for argument index 4 (INT_MIN, 82,308 gas). No interpreter rebuild or host class processing was used.
- Eight independent CLI cases (multiply, synchronized method, overloaded name, long descriptor, missing method, wrong argument count, bad magic, truncated class) reverted inside EVM. A 100-gas run failed with actual EVM out-of-gas consuming 100.
- Known caveat: local compiler dependency audit reports low/high findings through `solc`/`tmp`; these are build-time Node dependencies, not included in EVM runtime. No forced compiler downgrade or dependency change was made as part of acceptance.
