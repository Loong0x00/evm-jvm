#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVAC=/usr/lib/jvm/java-8-openjdk/bin/javac
OUT="$ROOT/test-fixtures/classes"
mkdir -p "$OUT" "$ROOT/test-fixtures/generated"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]); d=r/'test-fixtures/generated-src/probe'; d.mkdir(parents=True,exist_ok=True)
ops={
 'NoArg': 'list.toArray();',
 'Add': 'list.add(null);',
 'Get': 'list.get(0);',
 'Equals': 'list.equals(new Object());',
 'Hash': 'list.hashCode();',
 'Clone': 'new ArrayListRefusalCloneProbe().copy();',
}
for suffix,body in ops.items():
 name='ArrayListRefusal'+suffix+'Probe'
 parent=' extends ArrayList' if suffix=='Clone' else ''
 copy=' public Object copy() throws CloneNotSupportedException { return clone(); }' if suffix=='Clone' else ''
 listinit='ArrayList list = new ArrayList(); ' if suffix!='Clone' else ''
 (d/(name+'.java')).write_text('package probe;\nimport java.util.ArrayList;\npublic final class '+name+parent+' { '+copy+' public static void main(String[] args) throws Exception { '+listinit+body+' } }\n')
PY
"$JAVAC" -source 8 -target 8 -g:none -d "$OUT" \
  "$ROOT/test-fixtures/src/probe/ArrayListTypedToArrayProbe.java" \
  "$ROOT"/test-fixtures/generated-src/probe/*.java
python3 - "$ROOT" <<'PY'
import pathlib,sys,zipfile
r=pathlib.Path(sys.argv[1]); cls=r/'test-fixtures/classes'; gen=r/'test-fixtures/generated'; files=sorted(cls.rglob('*.class'))
def archive(path, selected):
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
  for p in selected:
   name=p.relative_to(cls).as_posix()
   info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0; z.writestr(info,p.read_bytes())
positive=[p for p in files if p.name in ('ArrayListTypedToArrayProbe.class','ArrayListTypedToArrayProbe$MisleadingSizeList.class')]
assert len(positive)==2
archive(gen/'typed-to-array-positive.zip',positive)
archive(gen/'all-generated-probes.zip',files)
raw=bytes.fromhex((r/'ArrayList.class.hex').read_text().strip())
with zipfile.ZipFile(gen/'raw-arraylist-bootstrap-replacement.zip','w',compression=zipfile.ZIP_STORED) as z:
 info=zipfile.ZipInfo('java/util/ArrayList.class',date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0; z.writestr(info,raw)
print('generated host-javac oracle fixture only:',len(files),'classes; positive=',(gen/'typed-to-array-positive.zip').stat().st_size,'all-probes=',(gen/'all-generated-probes.zip').stat().st_size,'raw-candidate-replacement=',(gen/'raw-arraylist-bootstrap-replacement.zip').stat().st_size)
PY
