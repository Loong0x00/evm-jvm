#!/usr/bin/env python3
"""Generated Java-8-only class-count controls; no original class/JAR input."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile

out=Path(sys.argv[1]).resolve(); assert not out.exists(); out.mkdir(); src=out/'src'; src.mkdir(); classes=out/'classes'; classes.mkdir()
counts=(17,18,24,25)
for count in counts:
    d=src/str(count); d.mkdir()
    tails=count-2 # CountMain + supplied java/lang/Runnable + all tails
    calls=' + '.join('Tail%02d.touch()'%n for n in range(1,tails+1))
    last='Tail%02d'%tails
    tracker='Tail%02d'%max(1,tails-1)
    # Runnable is supplied as a raw image, deliberately shortening the conditional bootstrap tail.
    (d/'Runnable.java').write_text('package java.lang; public interface Runnable { void run(); }\n')
    main=f'''public final class CountMain implements Runnable {{
  static int sentinel;
  public void run() {{ sentinel = {calls}; }}
  static void require(boolean ok) {{ if (!ok) throw new RuntimeException(); }}
  public static void main(String[] ignored) {{
    CountMain self = new CountMain();
    Runnable supplied = self;
    Class a = {last}.class, b = {last}.class;
    require(a == b); require({tracker}.seen == 0);
    require(a.getName().equals("{last}"));
    supplied.run();
    require({last}.touch() == {tails});
    require({tracker}.seen == 1);
    {last}[] from = new {last}[] {{ new {last}(), new {last}() }};
    {last}[] to = new {last}[2];
    System.arraycopy(from, 0, to, 0, 2);
    require(to[0] == from[0] && to[1] == from[1]);
    System.arraycopy(to, 0, to, 1, 1);
    require(to[1] == from[0]);
    sentinel += to.length;
  }}
}}\n'''
    (d/'CountMain.java').write_text(main)
    for n in range(1,tails+1):
        name='Tail%02d'%n
        if n==tails:
            body=f'final class {name} {{ static {{ {tracker}.seen++; }} static int touch() {{ return {n}; }} }}\n'
        elif n==tails-1:
            body=f'final class {name} {{ static int seen; static int touch() {{ return {n}; }} }}\n'
        else:
            body=f'final class {name} {{ static int touch() {{ return {n}; }} }}\n'
        (d/(name+'.java')).write_text(body)
    # Compile java.lang/Runnable separately, then the actual selected program against it.
    boot=out/('boot'+str(count)); boot.mkdir()
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-d',str(boot),str(d/'Runnable.java')],check=True)
    program=[str(p) for p in sorted(d.glob('*.java')) if p.name != 'Runnable.java']
    c=classes/str(count); c.mkdir()
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-g:none','-cp',str(boot),'-d',str(c),*program],check=True)
    subprocess.run(['/usr/lib/jvm/java-8-openjdk/bin/java','-cp',str(c),'CountMain'],check=True)
    entries=['CountMain.class']+['Tail%02d.class'%n for n in range(1,tails+1)]+['java/lang/Runnable.class']
    assert len(entries)==count
    with zipfile.ZipFile(out/(str(count)+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for name in entries:
            data=(boot/name).read_bytes() if name.startswith('java/') else (c/name).read_bytes()
            zi=zipfile.ZipInfo(name,(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; z.writestr(zi,data)
    receipt={'java8TESTOracle':True,'bindingCount':count,'entries':entries,
             'zipSHA256':hashlib.sha256((out/(str(count)+'.zip')).read_bytes()).hexdigest(),
             'classSHA256':{name:hashlib.sha256(((boot/name) if name.startswith('java/') else (c/name)).read_bytes()).hexdigest() for name in entries}}
    (out/(str(count)+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'java8TESTOracle':True,'counts':counts},indent=2))
