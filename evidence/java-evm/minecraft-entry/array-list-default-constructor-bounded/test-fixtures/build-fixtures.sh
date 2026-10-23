#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
JAVAC=/usr/lib/jvm/java-8-openjdk/bin/javac
OUT="$ROOT/test-fixtures/classes"
mkdir -p "$OUT"
"$JAVAC" -source 8 -target 8 -g:none -d "$OUT" "$ROOT"/test-fixtures/src/probe/ArrayListDefaultProbe.java "$ROOT"/test-fixtures/src/probe/ArrayListNegativeProbe.java "$ROOT"/test-fixtures/src/probe/ArrayListIntOnlyProbe.java "$ROOT"/test-fixtures/src/probe/ArrayListCloneProbe.java
mkdir -p "$ROOT/test-fixtures/classes/replacement"
"$JAVAC" -source 8 -target 8 -g:none -d "$ROOT/test-fixtures/classes/replacement" "$ROOT"/test-fixtures/src/replacement/java/util/ArrayList.java
python3 - "$ROOT" <<'PY'
import pathlib,subprocess,sys,zipfile
root=pathlib.Path(sys.argv[1]); src=root/'test-fixtures/src/probe/ArrayListRefusalProbe.java'; template=src.read_text()
ops={'add':'list.add(null);','iterator':'list.iterator();','typed-to-array':'list.toArray(new Object[0]);','equals':'list.equals(new Object());','hash':'list.hashCode();','get':'list.get(0);'}
out=root/'test-fixtures/classes'; generated=root/'test-fixtures/generated'; generated.mkdir(exist_ok=True)
entries={'default':'probe/ArrayListDefaultProbe.class','negative':'probe/ArrayListNegativeProbe.class','int-only':'probe/ArrayListIntOnlyProbe.class','clone':'probe/ArrayListCloneProbe.class'}
for name,body in ops.items():
 cname=f'ArrayListRefusal{name.title().replace("-","")}Probe'; text=template.replace('ArrayListRefusalProbe',cname).replace('OPERATION',body); path=generated/f'{cname}.java'; path.write_text(text)
 subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',str(out),str(path)],check=True)
 entries[name]=f'probe/{cname}.class'
entries['raw-replacement']='java/util/ArrayList.class'
for name,entry in entries.items():
 target=generated/f'{name}.zip'
 info=zipfile.ZipInfo(entry,date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_STORED; info.create_system=0; info.external_attr=0
 if name=='raw-replacement': data=(root/'test-fixtures/classes/replacement/java/util/ArrayList.class').read_bytes()
 else: data=(out/entry).read_bytes()
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as z: z.writestr(info,data)
 print(name,entry,target.stat().st_size)
PY
