#!/usr/bin/env python3
"""Fresh COPY-only EVM-PC attribution for the capacity density control.

Writes only a fresh ignored build/java-diff-mc-capacity-cost-* tree.  The copied
compiler query asks solc for debug products but compares deployed runtime bytes
against the parent capacity pin; no Solidity source or emitted runtime is edited.
"""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[4]
out=Path(sys.argv[1]).resolve()
assert out.parent==R/'build' and out.name.startswith('java-diff-mc-capacity-cost-') and not out.exists(),out
E=R/'evidence/java-evm/capacity-baseline/parent-97a926123'
env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(R/'jvmevm/runtime/node_modules'))
def run(a,**kw):
 kw.setdefault('cwd',R);kw.setdefault('env',env);kw.setdefault('check',True)
 return subprocess.run(list(map(str,a)),**kw)
# Reproduce the parent reconstruction byte-for-byte, except npm is installed only in
# this fresh COPY before its copied build scripts run (the repository has no modules).
out.mkdir(parents=True);(out/'tmp').mkdir()
def cp(rel,dst):
 b=(R/rel).read_bytes();want=subprocess.check_output(['git','show','7b46769c5:'+rel],cwd=R);assert b==want,rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
def patch(dst,name): subprocess.run(['patch','--batch','--forward',str(dst)],input=gzip.decompress((R/'evidence/java-evm/capacity-baseline/preflight/patches'/name).read_bytes()),cwd=R,check=True)
a=out/'capacityvfsassets'
for rel in ['VFS0aInterpreter.sol','build.js','assets.go','package.json','package-lock.json']: cp('jvmevm/runtime/local/vfs0a/'+rel,a/rel)
for q in (R/'jvmevm/runtime/local/vfs0a/bootstrap').rglob('*'):
 if q.is_file(): cp(str(q.relative_to(R)),a/'bootstrap'/q.relative_to(R/'jvmevm/runtime/local/vfs0a/bootstrap'))
patch(a/'VFS0aInterpreter.sol','vfs0a-capacity.patch.gz');(a/'assets.go').write_text((a/'assets.go').read_text().replace('package vfs0aassets','package capacityvfsassets'))
run(['npm','ci','--ignore-scripts'],cwd=a)
v=out/'capacityvfs/vfs0a.go';cp('jvmevm/localcontinuation/vfs0a/vfs0a.go',v);module='github.com/ethereum/go-ethereum/'+str(out.relative_to(R));v.write_text(v.read_text().replace('package vfs0a','package capacityvfs',1).replace('github.com/ethereum/go-ethereum/jvmevm/runtime/local/vfs0a',module+'/capacityvfsassets'))
c=out/'capacitycb0';rr=c/'runtime'
for rel in ['CB0ClassCoordinator.sol','build.js','assets.go','package.json','package-lock.json']: cp('jvmevm/localcontinuation/cb0/runtime/'+rel,rr/rel)
patch(rr/'CB0ClassCoordinator.sol','cb0-coordinator-capacity.patch.gz');patch(rr/'build.js','cb0-build-capacity.patch.gz')
for rel,pt in [('artifact.go','cb0-artifact.go.capacity.patch.gz'),('cb0.go','cb0-profile-capacity.patch.gz'),('head.go','cb0-head.go.capacity.patch.gz'),('session.go','cb0-session.go.capacity.patch.gz')]:
 cp('jvmevm/localcontinuation/cb0/'+rel,c/rel);patch(c/rel,pt);q=c/rel;q.write_text(q.read_text().replace('github.com/ethereum/go-ethereum/build/java-diff-mc-capacity-proto-smoke',module))
# Coordinator uses the same pinned compiler package; avoid a second install.
(rr/'node_modules').symlink_to(a/'node_modules')
for q in [v,a/'assets.go',*(c/x for x in ['artifact.go','cb0.go','head.go','session.go'])]: run(['gofmt','-w',q])
run(['node',a/'build.js'],stdout=(out/'vfs-build.log').open('w'),stderr=subprocess.STDOUT);run(['node',rr/'build.js'],stdout=(out/'coordinator-build.log').open('w'),stderr=subprocess.STDOUT)
va=json.loads((a/'artifacts/VFS0aInterpreter.json').read_text());assert hashlib.sha256(bytes.fromhex(va['deployedBytecode'].removeprefix('0x'))).hexdigest()=='4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f'
run(['python3',E/'repair_copy.py',out]);run(['python3',E/'build_drivers.py',out])
# Generate compiler debug products from the same copied patched sources/settings.
debug=out/'debug';debug.mkdir();(debug/'node_modules').symlink_to(a/'node_modules')
js=debug/'compile-debug.js';js.write_text(r'''const fs=require('fs'),solc=require('solc'),crypto=require('crypto');
if(solc.version()!=='0.8.30+commit.73712a01.Emscripten.clang')throw Error(solc.version());
const [src,out,contract]=process.argv.slice(2),text=fs.readFileSync(src,'utf8');
const settings={optimizer:{enabled:true,runs:200},viaIR:true,evmVersion:'cancun',metadata:{appendCBOR:false,bytecodeHash:'none'},outputSelection:{'*':{'':['ast'],'*':['abi','evm.bytecode.object','evm.deployedBytecode.object','evm.deployedBytecode.sourceMap','evm.deployedBytecode.generatedSources','evm.bytecode.sourceMap','metadata']}}};
let r=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{[require('path').basename(src)]:{content:text}},settings})));if((r.errors||[]).some(x=>x.severity==='error'))throw Error(JSON.stringify(r.errors));let c=r.contracts[require('path').basename(src)][contract];fs.writeFileSync(out,JSON.stringify({compiler:solc.version(),settings,sourceSHA256:crypto.createHash('sha256').update(text).digest('hex'),ast:r.sources[require('path').basename(src)].ast,contract:c},null,2)+'\n');''')
for name,src,contract,want in [
 ('vfs',out/'capacityvfsassets/VFS0aInterpreter.sol','VFS0aInterpreter','4a7f61989c5ec68edbee96d34cd97c7f0f54f26ffc30d8b351247bd26839f86f'),
 ('coordinator',out/'capacitycb0/runtime/CB0ClassCoordinator.sol','CB0ClassCoordinator',None)]:
 run(['node',js,src,debug/(name+'-solc.json'),contract])
 x=json.loads((debug/(name+'-solc.json')).read_text());b=bytes.fromhex(x['contract']['evm']['deployedBytecode']['object']);x['runtimeSHA256']=hashlib.sha256(b).hexdigest();x['runtimeBytes']=len(b);(debug/(name+'-receipt.json')).write_text(json.dumps(x,indent=2)+'\n')
 if want: assert x['runtimeSHA256']==want and len(b)==292968
# Replace only the copied generated main's observer with PC/call-frame aggregation.
p=out/'prototype/main.go';s=p.read_text()
s=s.replace('type observer struct {','type pcCost struct { Address string `json:"address"`; PC uint64 `json:"pc"`; Opcode uint8 `json:"opcode"`; Count uint64 `json:"count"`; Cost uint64 `json:"cost"`; Forwarded uint64 `json:"forwarded"` }\ntype frameCost struct { Depth int `json:"depth"`; Type uint8 `json:"type"`; From string `json:"from"`; To string `json:"to"`; EnterGas uint64 `json:"enterGas"`; Used uint64 `json:"used"`; Reverted bool `json:"reverted"`; Error string `json:"error,omitempty"` }\ntype observer struct {')
s=s.replace('\tEnabled       bool       `json:"enabled"`\n}', '\tEnabled       bool       `json:"enabled"`\n\tPCs map[string]*pcCost `json:"pcs"`\n\tFrames []frameCost `json:"frames"`\n}',1)
s=s.replace('o := &observer{}','o := &observer{PCs: map[string]*pcCost{}}',1)
s=s.replace('var began time.Time\n\thooks :=', 'var began time.Time\n\tframeAt := map[int][]int{}\n\tlastCall := map[int]string{}\n\thooks :=',1)
s=s.replace('if depth == 0 {\n\t\t\to.RootCalls++', 'if depth>0 { if k:=lastCall[depth]; k!="" { o.PCs[k].Forwarded+=gas; delete(lastCall,depth-1) } }; fi := len(o.Frames); o.Frames=append(o.Frames, frameCost{Depth:depth,Type:typ,From:from.Hex(),To:to.Hex(),EnterGas:gas}); frameAt[depth]=append(frameAt[depth],fi)\n\t\tif depth == 0 {\n\t\t\to.RootCalls++',1)
s=s.replace('if depth == 0 {\n\t\t\tt := time.Since(began).Seconds()', 'if z:=frameAt[depth];len(z)>0 { i:=z[len(z)-1]; frameAt[depth]=z[:len(z)-1]; o.Frames[i].Used=gas; o.Frames[i].Reverted=reverted; if e!=nil{o.Frames[i].Error=e.Error()} }\n\t\tif depth == 0 {\n\t\t\tt := time.Since(began).Seconds()',1)
s=s.replace('\t}}\n\tmust(setter.ParentTrace(hooks))', '''\t}}
\thooks.OnOpcode = func(pc uint64, op byte, gas, cost uint64, scope tracing.OpContext, rdata []byte, depth int, er error) { a:=scope.Address().Hex(); k:=fmt.Sprintf("%s/%d",a,pc); v:=o.PCs[k]; if v==nil { v=&pcCost{Address:a,PC:pc,Opcode:uint8(op)};o.PCs[k]=v }; v.Count++;v.Cost+=cost; if op==0xf0||op==0xf1||op==0xf2||op==0xf4||op==0xf5||op==0xfa { lastCall[depth]=k } }
\tmust(setter.ParentTrace(hooks))''',1)
# Setup is intentionally untraced: the target is the Java call and setup tracing
# would serialize unrelated AS0/ZI0/DI0 construction PCs.
s=s.replace('setupTrace := observe(s, cb0.Head{})','setupTrace := &observer{}',1)
p.write_text(s);run(['gofmt','-w',p]);run(['go','build','-trimpath','-o',out/'prototype/driver',p])
# Existing deterministic fixture builder supplies the two parent fixtures, opaque ZIP inputs.
run(['python3',R/'evidence/java-evm/capacity-baseline/fixture-completion/generate.py',out/'fixtures'])
# Density ZIP is the existing parent generation recipe, copied here without invoking host code at runtime.
src=out/'density-src';cls=out/'density-classes';src.mkdir();cls.mkdir();big=(E/'final/density/sources/BigEntry.java').read_text();(src/'BigEntry.java').write_text(big);(src/'BigTwin.java').write_text(big.replace('BigEntry','BigTwin'));(src/'BigPair.java').write_text('public class BigPair { public static int run(int x) { return BigEntry.use(x) + BigTwin.use(x) + 7; } }\n')
run(['/usr/lib/jvm/java-8-openjdk/bin/javac','-source','8','-target','8','-g:none','-d',cls,*src.glob('*.java')])
dzip=out/'density.zip'
with zipfile.ZipFile(dzip,'w') as z:
 for n in ['BigPair','BigEntry','BigTwin']:
  i=zipfile.ZipInfo(n+'.class',(1980,1,1,0,0,0));i.external_attr=0o100644<<16;z.writestr(i,(cls/(n+'.class')).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
assert sum((cls/(n+'.class')).stat().st_size for n in ['BigPair','BigEntry','BigTwin'])==181969
# Setup a fresh disk world, then run one ordinary receipt. Driver always collects PC aggregates.
def call(label,args,timeout=120):
 with (out/(label+'.json')).open('w') as so,(out/(label+'.stderr')).open('w') as se: run([out/'prototype/driver',*args],stdout=so,stderr=se,timeout=timeout)
 return json.loads((out/(label+'.json')).read_text())
def case(label,zp,names):
 world=out/('world-'+label);setup=call(label+'-setup',['-command','setup','-dir',world,'-zip',zp,'-names',names]);row=call(label+'-ordinary',['-command','slice','-dir',world,'-length',zp.stat().st_size,'-mode','7','-gas','100000000'],180);return {'setup':setup,'ordinary':row}
rows={'padded262144':case('padded262144',out/'fixtures/zips/aggregate262144.zip','BoundaryEntry,BoundaryPad'),'bigMethodRich':case('bigMethodRich',out/'fixtures/zips/big-method-rich.zip','BigCaller,BigEntry'),'density181969':case('density181969',dzip,'BigPair,BigEntry,BigTwin')}
(out/'raw-summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({k:{'gas':v['ordinary']['gas'],'error':v['ordinary'].get('error'),'root':v['ordinary']['afterRoot']} for k,v in rows.items()},indent=2))
