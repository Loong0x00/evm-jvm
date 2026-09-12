#!/usr/bin/env python3
"""Instrumentation of a copied generated public-CB0 driver; no runtime changes."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[4];s=(root/'evidence/java-evm/link-frontier/preflight/driver.go.txt').read_text()
s=s.replace('type output struct {','type output struct {\nLoadedStateRoot common.Hash `json:"loadedStateRoot"`\nReopenedASOCreated bool `json:"reopenedASOCreated"`',1)
s=s.replace('o := output{command,','o := output{h.StateRoot,false,command,',1)
s=s.replace('if reopened.EngineInstalled {','if reopened.EngineInstalled||reopened.AS0Creation.Performed||reopened.AS0Creation.GasUsed!=0 {',1)
s=s.replace('"command": "terminal",','"command": "terminal","stateRoot":h.StateRoot,"reopenedASOCreated":reopened.AS0Creation.Performed,',1)
s=s.replace('"command": "fifth-class-refusal",','"command": "fifth-class-refusal","pid":os.Getpid(),',1)
s=s.replace('''		after := head(s)
		selector, code, detail := refusal(r.RevertData)''','''        if r.Slice.Schema!=0||r.StateRoot!=(common.Hash{})||len(r.Checkpoint)!=0||len(r.Logs)!=0{panic("failed call leaked success fields")}
        after := head(s)
        if after.Java.Epoch>0 {cp,ce:=s.ReadCheckpoint(after.Java.CheckpointRoot);must(ce);if crypto.Keccak256Hash(cp)!=h.Java.CheckpointRoot{panic("prior checkpoint changed")}}
        selector, code, detail := refusal(r.RevertData)''',1)
s=s.replace('"command": "refusal",','"command": "refusal","reopenedASOCreated":reopened.AS0Creation.Performed,"reopenedEngineInstalled":reopened.EngineInstalled,"failedSliceSchema":r.Slice.Schema,"failedCheckpointBytes":len(r.Checkpoint),"failedLogs":len(r.Logs),"failedStateRoot":r.StateRoot,',1)
Path(sys.argv[1]).write_text(s)
