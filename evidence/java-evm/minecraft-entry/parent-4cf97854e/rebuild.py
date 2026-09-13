#!/usr/bin/env python3
"""Fresh source-only MC-ENTRY compiler rebuild and normal opaque-input Go driver."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];src=root/'evidence/java-evm/minecraft-entry/class-literal-preflight';out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-entry-parent-') and not out.exists();out.mkdir();(out/'tmp').mkdir();env=dict(os.environ,TMPDIR=str(out/'tmp'),NODE_PATH=str(root/'jvmevm/runtime/node_modules'))
for kind,name in [('engine','MCEntryInterpreter'),('coordinator','MCEntryCoordinator')]:
 d=out/kind;d.mkdir()
 for n in (name+'.sol','build.js'):shutil.copy2(src/kind/n,d/n)
 with (out/(kind+'-build.log')).open('w') as f:subprocess.run(['node',str(d/'build.js')],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 a=json.loads((d/(name+'.json')).read_text());ref=json.loads((src/kind/(name+'.json')).read_text());assert a==ref,(kind,'fresh compiler differs')
assert hashlib.sha256(bytes.fromhex(json.loads((out/'engine/MCEntryInterpreter.json').read_text())['deployedBytecode'])).hexdigest()=='a35a22d28314bcfcad05df73046d9ef7af08cfb6a5b24e3925f4ce1b9fee09fe'
subprocess.run([sys.executable,str(src/'bootstrap/build_runnable.py'),str(out/'runnable-bootstrap')],cwd=root,env=env,check=True)
subprocess.run([sys.executable,str(src/'bootstrap/build_class.py'),str(out/'class-bootstrap')],cwd=root,env=env,check=True)
s=(root/'evidence/java-evm/minecraft-entry/parent-cc6c876b4/executed_driver.go.txt').read_text()
for a,b in [('5cd308971f49e815ee8adf864133c05f44e675ae6efe6cabe771bd89ad8fb875','a35a22d28314bcfcad05df73046d9ef7af08cfb6a5b24e3925f4ce1b9fee09fe'),('2c841e15e382f6433adfbce3fddc225a5efeed5d0d87727c1eac4a0106f9d79f','838a37b319d197fc82c8db86645726e12d38c4d55a40186f59248b2e48de928c'),('06f642301333b90429e749951c7855cf954a379848d4643ef758f7853ff39a8c','62b80a209abdb7b809d34078a8003136cba3f0a1ceacd359eec9eb6de707242f'),('0x4d52304d41494e454e47494e4500000000000001','0x4d434c4153534c49544552414c00000000000001'),('294795','303045'),('MC-MR0/','MC-CLASS-LITERAL-PREFLIGHT/'),('MR0-SESSION-COPY-1','MC-CLASS-LITERAL-PARENT-COPY-1'),('len(m.Decoders) > 4','len(m.Decoders) > 16')]:
 assert a in s,a;s=s.replace(a,b)
a='func fixtureNames(zipPath string) [][]byte {';assert s.count(a)==1;s=s.replace(a,a+'''
 if names:=os.Getenv("MC_ENTRY_BINDINGS");names!="" {parts:=strings.Split(names,",");if len(parts)>16 {panic("binding count")};var out [][]byte;for _,p:=range parts {if p=="" {panic("empty binding")};out=append(out,[]byte(p))};return out}''')
a='"resourceReadReceipts": r.Trace.ResourceReads,';assert s.count(a)==1;s=s.replace(a,'"diagnostic":missingDiagnostic(r.Out), '+a)
a='"actualDI0ReadSizes": r.Trace.Reads, "nestedFrames": r.Trace.Nested, "sstoreOpcodes": r.Trace.SSTORE';assert s.count(a)==1;s=s.replace(a,'"resourceReadReceipts":r.Trace.ResourceReads,"resourceHashes":r.Trace.ResourceHashes, '+a)
s+='''
// Diagnostic EVM ABI only. No symbolic Java evaluation or execution fallback.
func missingDiagnostic(raw []byte) interface{} {
 er,ok:=engineABI.Errors["MCEntryMissingClass"];if !ok || len(raw)<4 || !bytes.Equal(raw[:4],er.ID[:4]) {return nil}
 v,x:=er.Inputs.Unpack(raw[4:]);must(x);b,x:=er.Inputs.Pack(v...);must(x);if !bytes.Equal(b,raw[4:]) {panic("noncanonical diagnostic")}
 return map[string]interface{}{"site":v[0].(*big.Int).String(),"context":v[1].(*big.Int).String(),"name":string(v[2].([]byte))}
}
'''
p=out/'main.go';p.write_text(s);subprocess.run(['gofmt','-w',str(p)],check=True);subprocess.run(['go','build','-trimpath','-o',str(out/'driver'),str(p)],cwd=root,env=env,check=True);subprocess.run(['go','vet',str(p)],cwd=root,env=env,check=True)
print('PASS fresh unchanged candidate engine/coordinator and adapted public transport')
