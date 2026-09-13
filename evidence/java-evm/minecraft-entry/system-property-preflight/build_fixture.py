#!/usr/bin/env python3
"""Build generated Java 8 fixtures; no original artifact is opened."""
from pathlib import Path
import shutil,subprocess,sys
out=Path(sys.argv[1]).resolve(); assert out.name=='fixture-classes' and out.parent.name.startswith('java-diff-mc-system-property-') and not out.exists(); out.mkdir()
fixtures=Path(__file__).resolve().parent/'fixtures'; javac='/usr/lib/jvm/java-8-openjdk/bin/javac'; rt='/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar'
def stripped(name, patterns):
 api=out.parent/name; shutil.copyfile(rt,api); subprocess.run(['zip','-q','-d',api,*patterns],check=True); return api
iae=stripped('rt-without-iae.jar',['java/lang/IllegalArgumentException.class'])
subprocess.run([javac,'-source','8','-target','8','-g:none','-bootclasspath',str(iae),'-d',str(out),str(fixtures/'IllegalArgumentException.java')],check=True)
# These generated probes intentionally compile against stock Java 8 signatures;
# the EVM resolves them only against its fixed guest System image.
ordinary=['SystemPropertyProbe.java','UnsupportedGetPropertiesProbe.java','UnsupportedSetPropertyProbe.java','UnsupportedClearPropertyProbe.java','RawSystemReplacementMain.java']
subprocess.run([javac,'-source','8','-target','8','-g:none','-d',str(out),*[str(fixtures/n) for n in ordinary]],check=True)
sysapi=stripped('rt-without-system.jar',['java/lang/System.class','java/lang/System$*.class'])
raw=out.parent/'raw-system-classes'; raw.mkdir()
subprocess.run([javac,'-source','8','-target','8','-g:none','-bootclasspath',str(sysapi),'-d',str(raw),str(fixtures/'raw/java/lang/System.java')],check=True)
