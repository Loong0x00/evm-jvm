#!/usr/bin/env python3
"""Repair isolated selected-table COPY metadata; observer/fault hooks remain COPY ONLY."""
from pathlib import Path
import json,sys
out=Path(sys.argv[1]).resolve();p=out/'selectedcb0/session.go';s=p.read_text()
assert s.count('MC-CB0/vm/v1')==1
s=s.replace('MC-CB0/vm/v1','MC-SELECTED-TABLE-PREFLIGHT/vm/v1')
s=s.replace('type Session struct {','type Session struct {\n parentTrace *tracing.Hooks',1)
s=s.replace('EVMConfig: vm.Config{}','EVMConfig: vm.Config{Tracer:s.parentTrace}',1)
p.write_text(s)
a=out/'selectedcb0/artifact.go';s=a.read_text();assert 'len(init)+2016' in s;s=s.replace('len(init)+2016','len(init)+3680');a.write_text(s)
b=out/'selectedcb0/runtime/build.js';s=b.read_text();assert 'maximumConstructorArguments = 4096' in s;b.write_text(s.replace('maximumConstructorArguments = 4096','maximumConstructorArguments = 3680'))
(out/'selectedcb0/parent_observer.go').write_text('''package selectedcb0
// COPY-ONLY test observer. No accepted public API or guest/state injection.
import("errors";"github.com/ethereum/go-ethereum/core/tracing")
func(s *Session) ParentTrace(h *tracing.Hooks)error{s.mu.Lock();defer s.mu.Unlock();if e:=s.cb0Usable();e!=nil{return e};s.parentTrace=h;return nil}
func(s *Session) ParentPublicationFault(enable bool)error{s.mu.Lock();defer s.mu.Unlock();if e:=s.cb0Usable();e!=nil{return e};s.testFault=nil;if enable{s.testFault=func(p cb0FaultPoint)error{if p==cb0FaultAfterTrie{return errors.New("parent after real trie/code sync")};return nil}};return nil}
''')
print(json.dumps({'experimentalGoRepair':'VM instance cache domain matches actual coordinator','constructorBytesToMeasure':3680,'experimentalObserver':'read-only EVM hooks, no effects on guest data/gas','fault':'COPY-only after actual trie/code sync, never accepted API'},indent=2))
