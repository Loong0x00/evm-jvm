#!/usr/bin/env python3
"""Real untouched-archive entry probe. No host Java/ZIP/class evaluator/parser."""
from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parents[4];out=Path(sys.argv[1]).resolve();assert out.parent==root/'build' and out.name.startswith('java-diff-mc-original-entry-') and not out.exists();out.mkdir();(out/'tmp').mkdir()
s=(root/'evidence/java-evm/main-root/atomicity-preflight/transport/atomicity_session.go.txt').read_text();p=out/'main.go';p.write_text(s)
subprocess.run([sys.executable,str(root/'evidence/java-evm/main-root/atomicity-parent-88a851a25/repair_copy.py'),str(p)],check=True);s=p.read_text()
a='switch filepath.Base(zipPath) {';assert s.count(a)==1;s=s.replace(a,a+'\ncase "minecraft_server.1.12.2.jar":\nreturn [][]byte{[]byte("net/minecraft/server/MinecraftServer.class"),[]byte("bn.class"),[]byte("tr.class"),[]byte("um.class")}')
a='names := fixtureNames(zipPath)';assert s.count(a)==1;s=s.replace(a,'if filepath.Base(zipPath)=="minecraft_server.1.12.2.jar" && (len(raw)!=30222121 || sha(raw)!="fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e") {panic("official opaque artifact hash differs")}\n'+a)
# Observe successful DI0 child returns only as transport bytes/hashes. Never feed
# any traced/decoded bytes back to execution or recover an unsuccessful snapshot.
s=s.replace('"io/fs"','"io/fs"\n"hash"',1)
s=s.replace('type callTrace struct {','type resourceRead struct { To common.Address; Offset uint32; Requested uint32; Returned uint32; Success bool; SHA256 string }\ntype callTrace struct {\nResourceReads []resourceRead\nResourceHashes map[string]string',1)
s=s.replace('if tr != nil {\n\t\thooks.OnEnter','if tr != nil {\n pendingReads:=map[int]int{}; resourceHashers:=map[common.Address]hash.Hash{};tr.ResourceHashes=map[string]string{}\n\t\thooks.OnEnter',1)
a='tr.Reads = append(tr.Reads, binary.BigEndian.Uint32(input[64:68]))';assert s.count(a)==1;s=s.replace(a,a+'''
 if len(input)!=68 || new(big.Int).SetBytes(input[4:36]).BitLen()>32 || new(big.Int).SetBytes(input[36:68]).BitLen()>32 {panic("noncanonical read input")}
 pendingReads[depth]=len(tr.ResourceReads);tr.ResourceReads=append(tr.ResourceReads,resourceRead{To:to,Offset:binary.BigEndian.Uint32(input[32:36]),Requested:binary.BigEndian.Uint32(input[64:68])})''')
a='hooks.OnExit = func(_ int, _ []byte, _ uint64, err error, _ bool) {';assert s.count(a)==1;s=s.replace(a,'''hooks.OnExit = func(depth int, output []byte, _ uint64, err error, reverted bool) {
 if index,ok:=pendingReads[depth];ok {
 delete(pendingReads,depth);r:=&tr.ResourceReads[index]
 if err==nil && !reverted {
  if len(output)<64 || new(big.Int).SetBytes(output[:32]).Uint64()!=32 || new(big.Int).SetBytes(output[32:64]).BitLen()>32 {panic("noncanonical read output")}
  n:=uint32(new(big.Int).SetBytes(output[32:64]).Uint64());if n!=r.Requested || n>4096 || len(output)!=64+int((n+31)/32)*32 {panic("read fragment shape")}
  for _,b:=range output[64+int(n):] {if b!=0 {panic("read padding")}}
  body:=output[64:64+int(n)];r.Returned=n;r.Success=true;r.SHA256=sha(body)
  h:=resourceHashers[r.To];if h==nil {if r.Offset!=0 {panic("first read offset")};h=sha256.New();resourceHashers[r.To]=h};h.Write(body);tr.ResourceHashes[r.To.Hex()]=hex.EncodeToString(h.Sum(nil))
 }
 }
''')
a='"checkpointBytes": 0, "candidateHead": "",';assert s.count(a)==1;s=s.replace(a,'"resourceReadReceipts":r.Trace.ResourceReads,"resourceHashes":r.Trace.ResourceHashes, '+a)
p.write_text(s);subprocess.run(['gofmt','-w',str(p)],check=True)
env=dict(os.environ,TMPDIR=str(out/'tmp'))
subprocess.run(['go','build','-trimpath','-o',str(out/'driver'),str(p)],cwd=root,env=env,check=True);subprocess.run(['go','vet',str(p)],cwd=root,env=env,check=True)
