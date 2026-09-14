# Parent catchable CNFE evidence

See JAVA_EVM_MC_CLASS_NOT_FOUND_PARENT_PREFLIGHT.md. Parent independently compiles
two exception images, validates every kind13 serialization bound, proves exact/super
catches and uncaught lifecycle3, then replays original to Class.forName.

parent-evidence.tar.gz allowlists generated reports/resources/opaque checkpoints;
archive-files hashes every member. No original JAR/class/page/LevelDB. Two harness
failures are retained and not credited; final execution uses only successful states.
