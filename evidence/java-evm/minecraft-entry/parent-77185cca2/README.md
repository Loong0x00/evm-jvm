# Parent ClassLoader.loadClass evidence

See JAVA_EVM_MC_CLASSLOADER_LOADCLASS_PARENT_PREFLIGHT.md. Parent maps shared mirror
quota to guest OOM, source-builds ClassLoader, runs combined prior/load/original under
a whole watchdog, and decodes the EVM-issued active String as javax.servlet.Servlet.
Host inventory confirms absence.

parent-evidence.tar.gz allowlists generated reports/resources/opaque checkpoints;
archive-files hashes all members. No original JAR/class/page/LevelDB. Four harness
failures are retained and not credited. Original failed state is never resumed.
