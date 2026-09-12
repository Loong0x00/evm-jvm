#!/usr/bin/env python3
"""Copy-only parent instrumentation of public-API generated replay, not CB0 edits."""
from pathlib import Path
import re,sys
root=Path(__file__).resolve().parents[4]
s=(root/'evidence/java-evm/main-entry/preflight/driver.go.txt').read_text()
s=s.replace('"path/filepath"','"path/filepath"\n"github.com/ethereum/go-ethereum/jvmevm/artifactstore/di0"')
s=s.replace('type output struct {','''var mutationReceipts []map[string]interface{}
var packageRefusal map[string]interface{}
var badPackage bool
func receipt(name string,op di0.Operation,e error){
 if e!=nil {panic(fmt.Sprintf("%s: %v revert=%x",name,e,op.RevertData))}
 if op.GasUsed==0||op.GasUsed>ordinaryGas||op.StateRoot==(common.Hash{}){panic("invalid mutation receipt")}
 mutationReceipts=append(mutationReceipts,map[string]interface{}{"method":name,"gas":op.GasUsed,"stateRoot":op.StateRoot})
}
type output struct {
 LoadedStateRoot common.Hash `json:"loadedStateRoot"`
 ReopenedASOCreated bool `json:"reopenedASOCreated"`
''',1)
s=s.replace('init, e := s.Initialization()\n\tmust(e)','init, e := s.Initialization()\n\tmust(e)\n var op di0.Operation\n if !init.EngineInstalled||!init.AS0Creation.Performed{panic("not a fresh initialized world")}\n receipt("InitialAS0Create",di0.Operation{GasUsed:init.AS0Creation.GasUsed,StateRoot:init.StateRoot},nil)',1)
a=s.index('func prepare(');b=s.index('// The two constants',a)
part=s[a:b]
pattern=r'_, e = s\.(Append|Seal|CreateIndex|DiscoverIndex|ScanIndex|FinishIndex|CreateDecoder|StepDecoder|PublishDecoder|CreateCoordinator)\(([^\n]*)\)\n(\s*)must\(e\)'
part,n=re.subn(pattern,lambda m:f'op, e = s.{m[1]}({m[2]})\n{m[3]}receipt("{m[1]}",op,e)',part)
assert n==10,n
needle='op, e = s.CreateCoordinator(common.Hash{}, refs, pkg, ordinaryGas)'
part=part.replace(needle,'''if badPackage {
  old:=head(s).StateRoot;wrong:=pkg;wrong[0]^=1
  refused,err:=s.CreateCoordinator(common.Hash{},refs,wrong,ordinaryGas)
  after:=head(s).StateRoot
  selector:=crypto.Keccak256([]byte("CB0Error(uint256)"))[:4]
  if err==nil||len(refused.RevertData)!=36||string(refused.RevertData[:4])!=string(selector)||refused.RevertData[35]!=16||after!=old||refused.StateRoot!=(common.Hash{}) {panic("wrong package was not exact atomic refusal")}
  packageRefusal=map[string]interface{}{"error":err.Error(),"revertData":fmt.Sprintf("0x%x",refused.RevertData),"gas":refused.GasUsed,"publishedRootBefore":old,"publishedRootAfter":after}
 }
 '''+needle,1)
s=s[:a]+part+s[b:]
s=s.replace('o := output{command,','o := output{h.StateRoot,false,command,',1)
s=s.replace('flag.Parse()','flag.BoolVar(&badPackage,"bad-package",false,"parent real bad assertion probe, then ordinary retry")\n flag.Parse()',1)
s=s.replace('"classCount": h.Coordinator.ClassCount,','"classCount": h.Coordinator.ClassCount,"mutationReceipts":mutationReceipts,"packageRefusal":packageRefusal,',1)
s=s.replace('if reopened.EngineInstalled {','if reopened.EngineInstalled || reopened.AS0Creation.Performed || reopened.AS0Creation.GasUsed!=0 {',1)
s=s.replace('"command": "terminal",','"command": "terminal","stateRoot":h.StateRoot,"reopenedASOCreated":reopened.AS0Creation.Performed,',1)
Path(sys.argv[1]).write_text(s)
