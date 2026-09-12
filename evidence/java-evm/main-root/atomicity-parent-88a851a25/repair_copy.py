#!/usr/bin/env python3
"""Parent COPY-only corrections for independently reproduced error/IO accounting gaps."""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
def edit(a,b):
 global s
 assert s.count(a)==1,a[:100]
 s=s.replace(a,b)
edit('''	candidate.Counters.DirectorySyncs++
	b, x := json.MarshalIndent(candidate, "", "  ")''','''	// Current directory sync happens AFTER publication and cannot truthfully
	// appear in these bytes yet. Published counters are conservative snapshots;
	// actual per-process IO is independently observed, not inferred on reopen.
	b, x := json.MarshalIndent(candidate, "", "  ")''')
edit('''	if x = e.faultAt("manifest-after-dirsync"); x != nil {''','''	e.m.Counters.DirectorySyncs++ // Only after actual successful syncDir.
	if x = e.faultAt("manifest-after-dirsync"); x != nil {''')
edit('''	if previousErr != nil {
		return fmt.Errorf("MR0 Session: read prior Head: %w", previousErr)
	}
	if previous.Root != old {
		return errors.New("MR0 Session: prior Head/root differs")
	}''','''	if previousErr != nil || previous.Root != old {
		// Authority cannot safely be reread/reconciled. Do not leave a live
		// candidate usable, and never overwrite the unreadable/divergent Head.
		cause := errors.New("MR0 Session: prior Head/root differs")
		if previousErr != nil { cause = fmt.Errorf("MR0 Session: read prior Head: %w", previousErr) }
		e.pendingCheckpoint = nil
		if restore := e.reload(old); restore != nil { cause = errors.Join(cause, restore) }
		e.poison = cause
		return cause
	}''')
edit('''			 x = errors.Join(x, errors.New("MR0 Session: public EVM call cancelled after 30s"))'''.replace('\t\t\t ', '\t\t\t'),'''			x = errors.Join(x, errors.New("MR0 Session: public EVM call cancelled by owned deadline"))''')
edit('''			 x = errors.Join(x, errors.New("MR0 Session: public EVM CREATE cancelled after 30s"))'''.replace('\t\t\t ', '\t\t\t'),'''			x = errors.Join(x, errors.New("MR0 Session: public EVM CREATE cancelled by owned deadline"))''')
a='''		e.m.Counters.TimeoutCancels++
	}
	r := callResult{Out: append([]byte(nil), out...), Gas: gas - left, Err: x, Trace: tr, ElapsedMS: ms}'''
assert s.count(a)==2
s=s.replace(a,'''		e.m.Counters.TimeoutCancels++
		out = nil // Host cancellation is not an EVM revert or successful result.
	}
	r := callResult{Out: append([]byte(nil), out...), Gas: gas - left, Err: x, Trace: tr, ElapsedMS: ms}''',1)
pos=s.index('func (e *env) create(')
tail=s[pos:];assert tail.count(a)==1
tail=tail.replace(a,'''		e.m.Counters.TimeoutCancels++
		out = nil
		a = common.Address{} // No cancelled CREATE output/address is published.
	}
	r := callResult{Out: append([]byte(nil), out...), Gas: gas - left, Err: x, Trace: tr, ElapsedMS: ms}''');s=s[:pos]+tail
p.write_text(s)
