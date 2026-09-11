# Parent production DI0 integration evidence — NOT accepted

See JAVA_EVM_MC_DI0_CANDIDATE_FINDINGS.md for exact pins/observations/remaining gates.
All input ZIP/raw/plain fixtures are generated trusted tests; no server payload.

- runtime-rebuild*: pinned actual artifact build --check.
- integrated-tests*: original integrated worker tests before parent changes.
- runtime-replay*: fresh reconstruction from tracked runtime-candidate/replay.sh;
  reports under runtime-replay/, no old report reuse. PIDs/timing/RSS environmental.
- stored-head-failure*: real legal65535-byte raw stored-DEFLATE header successfully
  committed in EVM, then original Go Head validator refused it. Strict test exit1.
  Reproduce on58b24981f with current parent_test.go and run only
  TestDI0ParentStoredBlockPendingHeadAndReopen; all test sources tracked in package.
- stored-fix-process-tests*: mode-aware fix plus14 genuine child-process stages.
- publication-size-tests*: actual sync fault counter, page CREATE rollback/retry,
  poison/exact reopen and plaintext cap/bounds/opaque name tests.
- parent-regression*: final current package+runtime tests, including seven COPIED
  impossible-state mode tests (not a live ownership claim), true process tests.
- relocated*: freshly compiled trimpath executable runs from source-free directory;
  children also run with source-free CWD. No source/runtime file used for execution.
- vet*, dependencies*, protected-paths.log: actual checks of accepted dependencies
  and unchanged protected/core identities, not a claim of full VFS/legacy rerun.

Every watchdog JSON records the exact command, observed process-group peak RSS,
elapsed/exit and20min/4GiB limit. Ordinary calls100Mgas; smaller negative gas probes
explicitly labeled. Never recover state/output from OOG diagnostics. Failed original
captures stay intact. Runtime report Persistence.finalRoot is a TRIE root, not F;
60 publications there belong to its driver, not the production Session tests.

The additional review worker was provider-blocked, produced no result, and is not
credited or retried. Parent tests/findings are independently written/executed.
