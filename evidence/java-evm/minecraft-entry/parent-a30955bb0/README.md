# Parent PrivilegedAction evidence

See JAVA_EVM_MC_PRIVILEGED_ACTION_PARENT_PREFLIGHT.md. rebuild.py proves the
worker delta reverses to the exact prior parent, fixes all domain identities and
source-builds new artifacts. smoke.py tests generated bridge/interface behavior.
frontier/q1_after_failure use only successful EVM checkpoints; initial q7 and
final q1 failures are preserved, never continuation authority.

parent-evidence.tar.gz explicitly allowlists generated fixtures, public receipts
and mutable checkpoints; archive-files.json hashes each. No original JAR/class/
page/LevelDB payload. Original q1 frames demonstrate committed LoaderUtil init;
ClassLoader error is a diagnostic only. Worker candidate domains/pins remain
historical and are not promoted.
