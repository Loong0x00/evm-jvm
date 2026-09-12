#!/usr/bin/env python3
"""Parent repairs an archived interrupted draft; no accepted production edits."""
from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'draft/driver.go.txt').read_text()
s=s.replace('type env struct {','var memoryMode bool\n\ntype env struct {').replace('\tm    manifest\n}', '\tm    manifest\n\tinitialCounters counters\n\tinitialRoot common.Hash\n\tpoison error\n}')
s=s.replace('\tReader common.Address\n}', '\tReader common.Address\n\tChangedWrites uint64\n\tNestedOOG bool\n}')
s=s.replace('hooks.OnOpcode = func(', '''var pending bool; var writeAddr common.Address; var writeKey,writeOld,writeNew common.Hash
        hooks.OnExit = func(_ int,_ []byte,_ uint64,err error,_ bool) {if errors.Is(err,vm.ErrOutOfGas){tr.NestedOOG=true}}
        hooks.OnOpcode = func(''')
s=s.replace('''			if op == byte(vm.SSTORE) {
				tr.SSTORE++
			}''','''            if pending {if writeOld!=writeNew && st.GetState(writeAddr,writeKey)==writeNew {tr.ChangedWrites++};pending=false}
            if op == byte(vm.SSTORE) {
                tr.SSTORE++
                stack:=scope.StackData();if err==nil && len(stack)>=2 {writeAddr=scope.Address();writeKey=common.Hash(stack[len(stack)-1].Bytes32());writeOld=st.GetState(writeAddr,writeKey);writeNew=common.Hash(stack[len(stack)-2].Bytes32());pending=true}
            }''')
s=s.replace('''	kv, e := leveldb.New(filepath.Join(dir, "state"), 16, 16, "shared-world-preflight", false)
	if e != nil {
		return nil, e
	}
	d := rawdb.NewDatabase(kv)''','''    var d durable
    if memoryMode {d=rawdb.NewMemoryDatabase()} else {
        kv,err:=leveldb.New(filepath.Join(dir,"state"),16,16,"shared-world-preflight",false);if err!=nil{return nil,err};d=rawdb.NewDatabase(kv)
    }''',1)
s=s.replace('st, e := state.New(types.EmptyRootHash,','st, e := state.New(types.EmptyRootHash,',1) # e is declared by this line
s=s.replace('StartedUTC: time.Now().UTC().Format(time.RFC3339)}}','StartedUTC: time.Now().UTC().Format(time.RFC3339)},counters{},types.EmptyRootHash,nil}')
s=s.replace('''	// A readable published manifest completed one file fsync, rename and parent
	// directory fsync beyond the counters serialized in that same manifest.
	m.Counters.ManifestFileSyncs++
	m.Counters.ManifestRenames++
	m.Counters.DirectorySyncs++
	x := &env{d, t, st, m.Root, dir, m}''','''    // Readability does NOT prove a directory fsync. Count only actual operations
    // within each process, never synthesize increments while reopening.
    x := &env{d,t,st,m.Root,dir,m,m.Counters,m.Root,nil}''')
s=s.replace('if m.Format != format || m.Context != context || m.Owner != owner || m.Engine != engine {', '''marker,me:=os.ReadFile(filepath.Join(dir,"STORE-FORMAT"))
    if me!=nil || string(marker)!=format+"\\n" || m.Format!=format || m.Context!=context || m.Owner!=owner || m.Engine!=engine || m.Root==(common.Hash{}) || m.Root==types.EmptyRootHash || m.EngineNonce!=0 || m.EngineCode!=common.HexToHash("0xe7f4de699588a3d58624e8ab717a00809759d112952ca1fac8bbc74637118c84") || len(m.Decoders)!=len(m.Names) || len(m.Decoders)!=len(m.ResourceRoots) || len(m.Decoders)!=len(m.Sizes) {''')
s=s.replace('func (e *env) close() { e.trie.Close(); e.disk.Close() }', '''func (e *env) close() {
 writeJSON(filepath.Join(e.dir,fmt.Sprintf("process-%d.json",os.Getpid())),map[string]interface{}{"pid":os.Getpid(),"initialRoot":e.initialRoot,"finalRoot":e.root,"initialCounters":e.initialCounters,"finalCounters":e.m.Counters,"poisoned":e.poison!=nil,"memoryDB":memoryMode})
 e.trie.Close(); e.disk.Close()
}''')
a=s.index('func (e *env) writeManifest() error {');b=s.index('func diskSize(',a)
s=s[:a]+'''var errRenamed=errors.New("manifest renamed; reopen required")
func (e *env) writeManifest() error {
 e.m.Root=e.root;e.m.UpdatedUTC=time.Now().UTC().Format(time.RFC3339)
 b,x:=json.MarshalIndent(e.m,"","  ");if x!=nil{return x}
 f,x:=os.CreateTemp(e.dir,".head-");if x!=nil{return x};name:=f.Name()
 if _,x=f.Write(append(b,'\\n'));x==nil{x=f.Sync();if x==nil{e.m.Counters.ManifestFileSyncs++}}
 if ce:=f.Close();x==nil{x=ce};if x!=nil{return x}
 if x=os.Rename(name,filepath.Join(e.dir,"durable-head.json"));x!=nil{return x};e.m.Counters.ManifestRenames++
 if x=syncDir(e.dir);x!=nil{return fmt.Errorf("%w: %v",errRenamed,x)};e.m.Counters.DirectorySyncs++
 return nil
}
func (e *env) persist(old common.Hash,fail bool) error {
 start:=time.Now();previous,previousErr:=readManifest(e.dir)
 restore:=func(){stats,pids:=e.m.Counters,e.m.ProcessPIDs;if previousErr==nil{e.m=previous;e.m.Counters=stats;e.m.ProcessPIDs=pids};if x:=e.reload(old);x!=nil{e.poison=x}}
 r,x:=e.st.Commit(1,true,true);if x==nil{x=e.trie.Commit(r,false)}
 if x==nil{x=e.disk.SyncKeyValue();if x==nil{e.m.Counters.TrieCodeSyncs++}}
 if x!=nil{restore();return x}
 if fail{restore();return errors.New("injected after actual trie+code sync before manifest publication")}
 e.root=r
 if x=e.writeManifest();x!=nil{if errors.Is(x,errRenamed){e.poison=x}else{restore()};return x}
 if x=e.reload(r);x!=nil{e.poison=x;return x}
 e.m.Counters.Commits++;e.m.Counters.CommitMS+=time.Since(start).Milliseconds()
 return nil
}
''' +s[b:]
a=s.index('func (e *env) recordCall(');b=s.index('func (e *env) call(',a)
old=s[a:b];obs=old.replace('func (e *env) recordCall(r callResult, mutation bool)', 'func (e *env) observeCall(r callResult)').replace('''	if mutation && r.Err == nil {
		e.m.Counters.Mutations++
	}''','')
s=s[:a]+obs+'''func (e *env) recordCall(r callResult,mutation bool){if mutation&&r.Err==nil{e.m.Counters.Mutations++}}
'''+s[b:]
s=s.replace('''	tr := callTrace{Reader: e.m.Coordinator}''','''    if e.poison!=nil{return callResult{Err:e.poison}}
    tr := callTrace{Reader:e.m.Coordinator}''')
s=s.replace('''	return callResult{append([]byte(nil), out...), gas - left, x, tr}''','''    r:=callResult{append([]byte(nil),out...),gas-left,x,tr};e.observeCall(r);return r''')
s=s.replace('''	return a, out, callResult{append([]byte(nil), out...), gas - left, x, tr}''','''    r:=callResult{append([]byte(nil),out...),gas-left,x,tr};e.observeCall(r);return a,out,r''')
s=s.replace('''	if x != nil {
		r.Err = x
	}
	return r
}''','''    if x!=nil{r.Err=x;r.Out=nil}
    return r
}''',1)
s=s.replace('e.st.IntermediateRoot(true)','e.st.Copy().IntermediateRoot(true)')
# Save the EVM-established coordinator route with the same publication as CREATE.
s=s.replace('''		e.m.Counters.Creates++
		e.recordCall(r, true)
		old := e.root''','''        e.m.Coordinator=at;e.m.CoordinatorCode=crypto.Keccak256Hash(run);e.m.PackageRoot=p
        e.m.Instance=common.Hash(view(e,a,at,"instanceId")[0].([32]byte));e.m.Total=view(e,a,at,"totalClassBytes")[0].(uint32)
        e.m.Counters.Creates++
        e.recordCall(r,true)
        old:=e.root''',1)
# Direct CALL low-gas profile refusal after the engine reentrancy SSTORE, without host restore first.
needle='''	r, d := coordinatorCall(e, ca, vabi, "start",'''
idx=s.index(needle)
s=s[:idx]+'''    probeData,_:=ca.Pack("start",[32]byte(p),uint8(0),"run",[]int32{input},q,uint32(4096))
    before:=e.st.Copy().IntermediateRoot(true);probe:=e.call(owner,at,probeData,500000);after:=e.st.Copy().IntermediateRoot(true)
    writeJSON(filepath.Join(dir,"java-write-refusal.json"),map[string]interface{}{"error":fmt.Sprint(probe.Err),"selector":selector(probe.Out),"code":new(big.Int).SetBytes(probe.Out[4:]).Uint64(),"gas":probe.Gas,"nestedOOG":probe.Trace.NestedOOG,"completedChangedSstores":probe.Trace.ChangedWrites,"before":before,"afterBeforeHostRestore":after})
    if probe.Err==nil || len(probe.Out)!=36 || errorName(vabi,probe.Out)!="LC0ControlError" || new(big.Int).SetBytes(probe.Out[4:]).Uint64()!=7 || probe.Trace.NestedOOG || probe.Trace.ChangedWrites==0 || before!=after {panic("direct Java post-write profile refusal proof failed")}
    must(e.reload(e.root))
'''+s[idx:]
s=s.replace('''	e.m.Stage = "started"
	must(e.writeManifest())''','''    e.m.Stage="started"
    if memoryMode {for e.m.Lifecycle==1 {cp:=readCheckpoint(e);rr,_:=coordinatorCall(e,ca,vabi,"resume",[32]byte(e.m.PackageRoot),e.m.Epoch,[32]byte(e.m.CheckpointRoot),cp,e.m.Quantum,uint32(4096));must(rr.Err)};e.m.Stage="memory-final"}
    must(e.writeManifest())''',1)
s=s.replace('''	case "setup-chain":''','''    case "setup-memory":
        memoryMode=true;q,_:=strconv.ParseUint(os.Args[5],10,64);in,_:=strconv.ParseInt(os.Args[6],10,32);setupChain(os.Args[2],os.Args[3],os.Args[4],q,int32(in))
    case "setup-chain":''',1)
# Commit/reload the coordinator binding with each construction; full production
# metadata validation is deliberately NOT claimed by this disposable driver.
# Parent adds count5 and distinct-decoder/same-name constructor boundaries.
needle='br.Failures = append(br.Failures, tryCreateFailure(e, "duplicate-decoder",'
at=s.index(needle)
s=s[:at]+"""br.Failures = append(br.Failures, tryCreateFailure(e,"five-class-count",ca,init,owner,e.m.Decoders[:5],names[:5],e.m.ResourceRoots[:5],e.m.Sizes[:5],nil,"2"))
    duplicate,dupRoot,dupSize:=createDecoder(e,e.m.Index,e.m.IndexRoot,names[0],true)
    br.Failures=append(br.Failures,tryCreateFailure(e,"duplicate-name-distinct-decoder",ca,init,owner,[]common.Address{e.m.Decoders[0],duplicate},[][]byte{names[0],names[0]},[]common.Hash{e.m.ResourceRoots[0],dupRoot},[]uint32{e.m.Sizes[0],dupSize},nil,"5"))
    """+s[at:]
s=s.replace("""	if d.Slice.Lifecycle == 1 {
		e.m.CheckpointSHA = writeCheckpoint(e, d.Checkpoint)
	} else {
		e.m.CheckpointSHA = ""
	}""","""    if len(d.Checkpoint)==0 || len(d.Checkpoint)>1<<20 || crypto.Keccak256Hash(d.Checkpoint)!=d.Slice.CheckpointRoot {panic("invalid EVM checkpoint bytes")}
    e.m.CheckpointSHA=writeCheckpoint(e,d.Checkpoint) // terminal blobs remain readable too
""")
s=s.replace('\te.m.Stage = "final-reopened"', '''    cp:=readCheckpoint(e);if crypto.Keccak256Hash(cp)!=e.m.CheckpointRoot{panic("reopened terminal checkpoint differs from EVM head")}
    e.m.Stage="final-reopened"
''')
(p/'driver.go.txt').write_text(s)
