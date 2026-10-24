#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVAC=/usr/lib/jvm/java-8-openjdk/bin/javac
OUT="$ROOT/test-fixtures/classes"
mkdir -p "$OUT"
"$JAVAC" -source 8 -target 8 -g:none -d "$OUT" \
  "$ROOT/test-fixtures/src/probe/ArrayListIteratorProbe.java"
mkdir -p "$ROOT/test-fixtures/generated"
python3 - "$ROOT" <<'PY'
import pathlib,sys,zipfile
r=pathlib.Path(sys.argv[1]); cls=r/'test-fixtures/classes'; out=r/'test-fixtures/generated'; out.mkdir(exist_ok=True)
files=sorted(cls.rglob('*.class'))
with zipfile.ZipFile(out/'iterator-positive.zip','w',compression=zipfile.ZIP_STORED) as z:
 for p in files:
  name=p.relative_to(cls).as_posix(); info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0; z.writestr(info,p.read_bytes())
print('positive raw classes',len(files),'bytes',(out/'iterator-positive.zip').stat().st_size)
PY
mkdir -p "$ROOT/test-fixtures/raw-helper-src/java/util" "$ROOT/test-fixtures/raw-helper-classes"
cat > "$ROOT/test-fixtures/raw-helper-src/java/util/ArrayList\$Itr.java" <<'JAVA'
package java.util;
public final class ArrayList$Itr { }
JAVA
"$JAVAC" -source 8 -target 8 -g:none -d "$ROOT/test-fixtures/raw-helper-classes" "$ROOT/test-fixtures/raw-helper-src/java/util/ArrayList\$Itr.java"
python3 - "$ROOT" <<'PY'
import pathlib,sys,zipfile
r=pathlib.Path(sys.argv[1]); p=r/'test-fixtures/raw-helper-classes/java/util/ArrayList$Itr.class'; z=r/'test-fixtures/generated/raw-helper-replacement.zip'; info=zipfile.ZipInfo('java/util/ArrayList$Itr.class',date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0
with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_STORED) as f: f.writestr(info,p.read_bytes())
print('raw helper replacement bytes',p.stat().st_size)
PY
# One generated Java 8 entry per intentionally unsupported ArrayList API.
mkdir -p "$ROOT/test-fixtures/refusal-src/probe" "$ROOT/test-fixtures/refusal-classes"
python3 - "$ROOT" <<'PY'
import pathlib,subprocess,sys,zipfile
r=pathlib.Path(sys.argv[1]); src=r/'test-fixtures/refusal-src/probe'; out=r/'test-fixtures/refusal-classes'; gen=r/'test-fixtures/generated'
ops={'add':'list.add(null);','get':'list.get(0);','to-array':'list.toArray(new Object[0]);','equals':'list.equals(new Object());','hash':'list.hashCode();','clone':'new CloneList().copy();'}
for op,body in ops.items():
 name='ArrayListRefusal'+''.join(x.title() for x in op.split('-'))+'Probe'
 extra=''
 if op=='clone': extra='static final class CloneList extends ArrayList { Object copy() throws CloneNotSupportedException { return clone(); } }\n'
 text=f'''package probe;\nimport java.util.ArrayList;\npublic final class {name} {{\n {extra} public static void main(String[] args) throws Exception {{ ArrayList list = new ArrayList(); {body} }}\n}}\n'''
 path=src/(name+'.java');path.write_text(text)
 subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',str(out),str(path)],check=True)
 entries=[f'probe/{name}.class']
 if op=='clone': entries.append('probe/ArrayListRefusalCloneProbe$CloneList.class')
 z=gen/f'refusal-{op}.zip'
 with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_STORED) as f:
  for entry in entries:
   p=out/entry; info=zipfile.ZipInfo(entry,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0; f.writestr(info,p.read_bytes())
 print(op,[(e,(out/e).stat().st_size) for e in entries],z.stat().st_size)
# Private-helper name replacement is a deliberately rejected raw input.
helper= r/'test-fixtures/raw-helper-classes/java/util/ArrayList$Itr.class'
probe=src/'ArrayListRefusalAddProbe.java'
with zipfile.ZipFile(gen/'raw-helper-replacement.zip','w',compression=zipfile.ZIP_STORED) as f:
 for entry,p in [('java/util/ArrayList$Itr.class',helper),('probe/ArrayListRefusalAddProbe.class',out/'probe/ArrayListRefusalAddProbe.class')]:
  info=zipfile.ZipInfo(entry,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0; f.writestr(info,p.read_bytes())
PY
