Generated Java8 SharedEntry/SharedHelper fixture, NOT server bytes.
Source and deterministic ZIP builder:
evidence/java-evm/class-bridge/shared-world-parent-d76a45057/
Expected run(7)=317, run(9)=299; both execute real cross-class static initialization.
The transport tests upload only this opaque ZIP; no host class extraction/evaluation.

boundary-seven.zip: exact generated seven-image fixture from the same archived
shared-world parent generate_fixtures.py, freshly reproduced in
build/java-diff-mc-cb0-runtime-parent-1ec057f00/fixtures/ during parent acceptance.
Tests upload the ENTIRE opaque ZIP, select four FINAL EVM resources for exact65536
and65537 class package cases; no host class extraction in execution transport.

fault.zip: CB0Fault.java built by /usr/lib/jvm/java-8-openjdk/bin/javac
-source 8 -target 8 -g:none, Java8u504. Python ZipInfo('CB0Fault.class',
(1980,1,1,0,0,0)), ZIP_DEFLATED, writestr of that generated class. This fixture
proves an ordinary Java ArithmeticException has a published terminal checkpoint.
No server/JRE copyrighted payload, fake ready string or host evaluator is embedded.
