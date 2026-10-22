#!/usr/bin/env python3
"""Generate trusted Java 8 array-count boundaries; fixture logic stays ordinary/eager."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=Path(sys.argv[1]).resolve(); assert OUT.parent==ROOT/'build' and OUT.name.startswith('java-diff-mc-max-arrays-8192-fixtures-') and not OUT.exists()
OUT.mkdir(); rows=[]
for target in (8,4096,4097,8192,8193):
 name=f'ArrayCount{target}'; binary=f'generated/{name}'; entry=binary+'.class'; src=OUT/(name+'.java')
 # The canonical empty main argument is one array. Keep an outer reference array
 # and all inner arrays live; assignments are real alias-preserving heap writes.
 count=target-2
 src.write_text(f'''package generated; public final class {name} {{\n public static void main(String[] args) {{\n  Object[] refs = new Object[{count}];\n  for (int i=0;i<{count};i++) refs[i]=new int[0];\n  for (int i=0;i<{count};i++) if (refs[i]==null) throw new AssertionError();\n }}\n}}\n''')
 cls=OUT/'generated'/(name+'.class'); subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-d',str(OUT),str(src)],check=True)
 data=cls.read_bytes(); zp=OUT/(f'array-count-{target}.zip')
 with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_STORED) as z:z.writestr(entry,data)
 row={'requestedOrdinaryArrays':target,'implicitMainStringArray':1,'outerReferenceArray':1,'innerArrays':count,'entry':entry,'classBytes':len(data),'classSHA256':hashlib.sha256(data).hexdigest(),'zipSHA256':hashlib.sha256(zp.read_bytes()).hexdigest(),'sourceSHA256':hashlib.sha256(src.read_bytes()).hexdigest(),'ordinaryArrayElements':count}
 (OUT/f'array-count-{target}.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
(OUT/'manifest.json').write_text(json.dumps({'schema':1,'generatedJava8Only':True,'noOriginalInputs':True,'fixtures':rows},indent=2)+'\n'); print(json.dumps(rows,indent=2))
