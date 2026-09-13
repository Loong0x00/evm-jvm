#!/usr/bin/env python3
"""COPY-only keep telemetry out of unbounded authority metadata; no quota increase."""
from pathlib import Path
import os,shutil,subprocess,sys
root=Path(__file__).resolve().parents[4];base=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();(out/'tmp').mkdir()
for d in ('engine','coordinator'):shutil.copytree(base/d,out/d)
s=(base/'main.go').read_text()
a='MC-MARKER-MAP-PARENT-COPY-1';assert a in s;s=s.replace(a,'MC-MARKER-MAP-PARENT-BOUNDED-1')
a='type counters struct {';assert s.count(a)==1;s=s.replace(a,a+'\nReadFragmentCount uint64 `json:"readFragmentCount"`\nReadByteCount uint64 `json:"readByteCount"`')
a='e.m.Counters.ReadSizes = append(e.m.Counters.ReadSizes, r.Trace.Reads...)';assert s.count(a)==1;s=s.replace(a,'''// Full fragments remain in per-call observer receipts, not authoritative Head.
 e.m.Counters.ReadFragmentCount += uint64(len(r.Trace.Reads))
 for _,n:=range r.Trace.Reads {e.m.Counters.ReadByteCount+=uint64(n)}
 e.m.Counters.ReadSizes=nil''')
a='m.ProcessPIDs = append(m.ProcessPIDs, os.Getpid())';assert s.count(a)==1;s=s.replace(a,'m.ProcessPIDs = []int{os.Getpid()} // full process history is in external process receipts')
a='''b, x := json.MarshalIndent(candidate, "", "  ")
	if x != nil {
		return x
	}''';assert s.count(a)==1;s=s.replace(a,a+'\nif len(b)+1>32768 {return errors.New("COPY Head exceeds existing32768B bound")}')
p=out/'main.go';p.write_text(s);env=dict(os.environ,TMPDIR=str(out/'tmp'));subprocess.run(['gofmt','-w',str(p)],check=True);subprocess.run(['go','build','-trimpath','-o',str(out/'driver'),str(p)],cwd=root,env=env,check=True);subprocess.run(['go','vet',str(p)],cwd=root,env=env,check=True)
