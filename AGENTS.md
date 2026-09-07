# Java-inside-EVM M1 guide

Work from this Git repository (`/home/user/evm-jvm/geth`) on branch
`java-on-evm`. `upstream` is go-ethereum v1.16.9 at
`95665d5703e1023995a0ff93e4ce9eb77e8a59bd`. Before Git operations, confirm
`git rev-parse --show-toplevel`; the parent home directory has an unrelated Git
repository. Use `git status --short --branch`, stage explicit task paths, make
small verified local commits, and do not push.

Primary M1 interpreter path:

- Solidity generic interpreter source/artifact/build: `jvmevm/runtime/`
- Raw-byte ABI runner: `jvmevm/`
- CLI: `cmd/jvmevm/`
- Java inputs: `examples/java/Add.java`, `examples/java/Identity.java`
- Boundary, limits, and quickstart: `JAVA_EVM.md`
- Authoritative completed task record: `JAVA_EVM_INTERPRETER_PLAN.md`

At run time the host may only ABI-pack an unchanged raw classfile, method name,
and int arguments. The same generic EVM runtime parses the classfile and
constant pool, finds Code, and interprets `iload`/short forms, `iadd`, and
`ireturn` inside geth's EVM. Do not add host parsing, extraction, translation,
Java/Go evaluation, native precompiles, or specialized runtime generation to
this path. It is a tiny static-int JVM subset, not a full JVM.

Requires Go 1.24+, a JDK supporting `javac --release 8`, Node/npm, and make.
Run `make java-demo` for the true interpreter `20 + 22 = 42` pipeline and
`make java-test` for lockfile-pinned source/artifact consistency, uncached
focused tests, and CLI compilation. Build the CLI alone with
`go build -o build/bin/jvmevm ./cmd/jvmevm`. Regenerate/check the generic runtime
with `make java-runtime-build` / `make java-runtime-check`; compiler and settings
are documented in `JAVA_EVM.md`. Keep consensus VM core unchanged.

The M0 host-AOT translator remains as a clearly labeled baseline in `javaevm/`
and `cmd/javaevm/`; use only `make java-aot-demo` and `make java-aot-test` for
it. Do not muddle M0 AOT claims with the M1 in-EVM interpreter.

Do not expand this milestone to loops, arrays, objects, additional arithmetic,
class libraries, deployment, or Minecraft without a new scoped plan.
