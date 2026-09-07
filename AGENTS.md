# Java-on-EVM M0 guide

Work from this Git repository (`/home/user/evm-jvm/geth`) on branch `java-on-evm`.
`upstream` is go-ethereum v1.16.9 at `95665d5703e1023995a0ff93e4ce9eb77e8a59bd`.
Before Git operations, confirm `git rev-parse --show-toplevel`; the parent home
directory has an unrelated Git repository. Use `git status --short --branch`,
stage explicit task paths, and make small verified local commits. Do not push.

- Translator and geth-EVM harness: `javaevm/`
- CLI: `cmd/javaevm/`
- Minimal Java input: `examples/java/Add.java`
- User-facing limits and quickstart: `JAVA_EVM.md`

Requires Go 1.24+, a JDK supporting `javac --release 8`, and make.
Run `make java-demo` for the `20 + 22 = 42` pipeline and `make java-test` for uncached focused tests plus CLI compilation. For a standalone CLI: `go build -o build/bin/javaevm ./cmd/javaevm`. This is intentionally an AOT translator for one tiny static-int subset, not a JVM or on-chain deployment. Keep consensus VM core unchanged.

Next smallest task after M0: constants and subtraction (then comparisons/loops, static calls, heap/objects).
