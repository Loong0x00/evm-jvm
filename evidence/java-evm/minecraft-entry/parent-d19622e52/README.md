# Parent ClassLoader type evidence

See JAVA_EVM_MC_CLASSLOADER_TYPE_PARENT_PREFLIGHT.md. rebuild.py compiles the
minimal type, reverses candidate delta to exact prior source and matches complete
artifacts. smoke.py verifies generated semantics. frontier/q1_after_failure keep
failed diagnostics separate and resume only successful same-code checkpoints.
first-failure records the parent reverse-checker harness mistake.

parent-evidence.tar.gz allowlists generated fixtures, public receipts and mutable
checkpoints, each hashed by archive-files.json. No original JAR/class/page/LevelDB.
Worker per-child watchdog proves its headline RSS summary wrong; parent outer
watchdog is authoritative. Original frames establish committed ClassLoader array
path; missing Thread error is not continuation state.
