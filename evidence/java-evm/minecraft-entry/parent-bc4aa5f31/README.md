# Parent system ClassLoader evidence

See JAVA_EVM_MC_SYSTEM_CLASSLOADER_PARENT_PREFLIGHT.md. rebuild.py enforces the
320 failure then compiles identical source under LOCAL384, with parent identities.
smoke.py verifies canonical loader equality and preserves unsupported getResources.
frontier/q1_after_failure continue only successful checkpoints.

parent-evidence.tar.gz allowlists generated fixtures/public receipts/mutable CPs,
hashed in archive-files. No original JAR/class/page/LevelDB. First-failure records
the parent's overbroad source assertion. Original frames prove system getter and
all loader-array stores committed; LinkedHashSet remains a diagnostic only.
