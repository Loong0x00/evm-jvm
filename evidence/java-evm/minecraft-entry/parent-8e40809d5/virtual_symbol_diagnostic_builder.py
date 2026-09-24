from pathlib import Path
import json,os,re,shutil,subprocess
r=Path('/home/user/evm-jvm/geth');s=r/'build/java-diff-mc-object-hash-code-original-authorized-parent-8e40809d5';o=r/'build/java-diff-mc-post-object-hash-virtual-symbol-diagnostic-parent-8e40809d5'
assert not o.exists();shutil.copytree(s,o)
old='MC-RANDOM-CLASS-P14';new='MC-RANDOM-CLASS-D15';addr='0x4d432d52414e444f4d2d434c4153532d50310032';owner='0x4d432d52414e444f4d2d434c4153532d50310033';env={**os.environ,'NODE_PATH':str(r/'jvmevm/runtime/node_modules')}
def root_from_source(src,domain):
 """Hash the exact Solidity h[0..96] RHS, not a stale pin or a guessed image list."""
 body=src[src.index('    function _bootstrapRoot('):];body=body[:body.index('\n    function ',1)];assignments={int(i):rhs.strip() for i,rhs in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',body)};assert set(assignments)==set(range(97));pairs=[]
 for i in range(97):
  rhs=assignments[i];f=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',rhs)
  if f:
   p=src.index('    function '+f.group(1)+'(');b=src[p:];b=b[:b.index('\n    function ',1)];hexes=re.findall(r'hex"([0-9a-f]+)"',b);assert len(hexes)==1,(i,len(hexes));pairs.append(['image',hexes[0]]);continue
  assert re.fullmatch(r'DBOOT_[A-Z_]+',rhs),(i,rhs)
  expr=re.search(r'bytes32 private constant '+rhs+r'\s*=\s*([^;]+);',src).group(1).strip();assert expr.startswith('hex"') or expr.startswith('keccak256(hex"'),(i,rhs)
  hexes=re.findall(r'hex"([0-9a-f]+)"',expr);assert len(hexes)==1
  pairs.append(['hexhash' if expr.startswith('hex"') else 'image',hexes[0]])
 node='''const fs=require('fs'),{keccak256}=require('js-sha3');const a=JSON.parse(fs.readFileSync(0,'utf8'));const k=s=>keccak256(Buffer.from(s,'hex'));const w=n=>Buffer.from(BigInt(n).toString(16).padStart(64,'0'),'hex');const hs=a.pairs.map(([t,v])=>t==='image'?k(v):v);const x=Buffer.concat([Buffer.from(keccak256(a.domain),'hex'),w(64),w(hs.length),...hs.map(v=>Buffer.from(v,'hex'))]);console.log(keccak256(x));'''
 x=subprocess.run(['node','-e',node],input=json.dumps({'pairs':pairs,'domain':domain}),text=True,capture_output=True,cwd=r,env=env,check=True).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',x);return x
e=o/'engine';p=e/'MCEntryInterpreter.sol';x=p.read_text();assert x.count(old)==9;x=x.replace(old,new);needle='if (link == 0 || link == type(uint256).max) revert CallError(3, pc);';assert x.count(needle)==3
pos=x.rfind(needle);x=x[:pos]+x[pos:].replace(needle,'if (link == 0 || link == type(uint256).max) _diagnoseStaticSymbol(classes[owner], caller.data, nameOffset, nameLength, descriptorOffset, descriptorLength, pc);',1)
oldref='revert CallError(3, pc);';assert x.count(oldref)==12
for i in range(12): x=x.replace(oldref,f'revert CallError({3001+i}, pc);',1)
marker='    function _resolveCall('
helper='''    // Fresh-domain EVM-only diagnostic of a statically unresolved method; never installed.
    function _diagnoseStaticSymbol(
        ClassInfo memory ownerInfo, bytes memory callerData,
        uint256 nameOffset, uint256 nameLength,
        uint256 descriptorOffset, uint256 descriptorLength, uint256 pc
    ) private pure {
        bytes memory joined = new bytes(ownerInfo.thisNameLength + nameLength + descriptorLength + 2);
        uint256 at;
        for (uint256 i; i < ownerInfo.thisNameLength; ++i) joined[at++] = ownerInfo.data[ownerInfo.thisNameOffset + i];
        joined[at++] = bytes1(uint8(0x7c));
        for (uint256 i; i < nameLength; ++i) joined[at++] = callerData[nameOffset + i];
        joined[at++] = bytes1(uint8(0x7c));
        for (uint256 i; i < descriptorLength; ++i) joined[at++] = callerData[descriptorOffset + i];
        _missingClass(0x1023, pc, joined, 0, joined.length);
    }

'''
assert x.count(marker)==1;x=x.replace(marker,helper+marker)
missing_virtual = 'if (!foundInterface) revert CallError(3007, pc);'
assert x.count(missing_virtual)==1
x=x.replace(missing_virtual, 'if (!foundInterface) _diagnoseStaticSymbol(classes[symbolic], caller.data, out.nameOffset, out.nameLength, out.descriptorOffset, out.descriptorLength, pc);')
p.write_text(x)
with (o/'engine-build.log').open('w') as f:subprocess.run(['node',e/'build.js'],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
ea=json.loads((e/'MCEntryInterpreter.json').read_text());sz=len(ea['deployedBytecode'])//2;assert sz<=393216
c=o/'coordinator';p=c/'MCEntryCoordinator.sol';x=p.read_text();assert x.count(old)==4;x=x.replace(old,new);x,n=re.subn(r'address private constant ENGINE = .*?;',f'address private constant ENGINE = address(bytes20(hex"{addr[2:]}"));',x);assert n==1;x,n=re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";',f'bytes32 private constant ENGINE_CODEHASH = hex"{ea["codeHashes"]["runtimeKeccak256"]}";',x);assert n==1;p.write_text(x)
with (o/'coordinator-build.log').open('w') as f:subprocess.run(['node',c/'build.js'],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
ca=json.loads((c/'MCEntryCoordinator.json').read_text());cs=len(ca['deployedBytecode'])//2
p=o/'main.go';x=p.read_text()
for a,b in [(old,new),('0x4d432d52414e444f4d2d434c4153532d50310030',addr),('0x4d432d52414e444f4d2d434c4153532d50310031',owner)]:assert a in x;x=x.replace(a,b)
for name,value in [('immutableEngineSHA256',ea['codeHashes']['runtimeSHA256']),('immutableEngineKeccak','0x'+ea['codeHashes']['runtimeKeccak256']),('immutableCoordinatorKeccak','0x'+ca['codeHashes']['runtimeKeccak256'])]:x,n=re.subn(r'(const '+name+r' = ")[^"]+("\n)',r'\g<1>'+value+r'\g<2>',x);assert n==1
for name,value in [('engineRun',sz),('coordRun',cs),('run',sz)]:x,n=re.subn(r'(len\('+name+r'\) != )\d+',r'\g<1>'+str(value),x);assert n==1
p.write_text(x);subprocess.run(['gofmt','-w',p],check=True);subprocess.run(['go','build','-trimpath','-o',o/'driver',p],cwd=r,check=True);subprocess.run(['go','vet',p],cwd=r,check=True)
pins=json.loads((r/'build/java-diff-mc-object-hash-code-build-parent-8e40809d5/pins.json').read_text());pins.update(domain=new,address=addr,owner=owner,bootstrapRoot=root_from_source((e/'MCEntryInterpreter.sol').read_text(),'JVMEVM:MC-RANDOM-CLASS-D15:BOOTSTRAP:1'),engine={'bytes':sz,**ea['codeHashes']},coordinator={'bytes':cs,**ca['codeHashes']});(o/'pins.json').write_text(json.dumps(pins,indent=2)+'\n');print({'runtimeBytes':sz,'domain':new,'engineHash':ea['codeHashes']['runtimeKeccak256']})
