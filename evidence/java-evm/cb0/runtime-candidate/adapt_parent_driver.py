#!/usr/bin/env python3
"""Adapt the retained shared-world EVM driver to the frozen CB0 artifact schema.

The driver remains an ignored, controller-only EVM replay harness. This adapter only
changes production CB0 domains/error name and its artifact JSON reader; it does not
supply raw class bytes to the CB0 execution API or change its test positives.
"""
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:])
s = source.read_text()
s = s.replace('const format = "MC-SHARED-WORLD-PREFLIGHT-1"', 'const format = "JVMEVM-MC-CB0-LOCAL-STORE-1\\n"')
s = s.replace('var packageDomain = crypto.Keccak256Hash([]byte("MC-SHARED-WORLD-PREFLIGHT/package/v1"))', 'var packageDomain = crypto.Keccak256Hash([]byte("MC-CB0/package/v1"))')
s = s.replace('var resourceDomain = crypto.Keccak256Hash([]byte("MC-SHARED-WORLD-PREFLIGHT/resource/v1"))', 'var resourceDomain = crypto.Keccak256Hash([]byte("MC-CB0/resource/v1"))')
s = s.replace('f.Name != "CoordinatorError"', 'f.Name != "CB0Error"')
old = '''\tCompiler     string                 `json:"compiler"`
\tSettings     map[string]interface{} `json:"settings"`
\tSourceSHA    string                 `json:"sourceSHA256"`
\tInitBytes    int                    `json:"initBytes"`
\tRuntimeBytes int                    `json:"runtimeBytes"`
\tInitSHA      string                 `json:"initSHA256"`
\tRuntimeSHA   string                 `json:"runtimeSHA256"`'''
new = '''\tCompiler     struct { Version string `json:"version"` } `json:"compiler"`
\tSettings     map[string]interface{} `json:"-"`
\tSourceSHA    string                 `json:"-"`
\tInitBytes    int                    `json:"-"`
\tRuntimeBytes int                    `json:"-"`
\tInitSHA      string                 `json:"-"`
\tRuntimeSHA   string                 `json:"-"`'''
if old not in s:
    raise SystemExit('parent driver artifact schema was not the retained expected form')
s = s.replace(old, new)
old = '"compiler": art.Compiler, "settings": art.Settings, "sourceSHA256": art.SourceSHA, "initSHA256": art.InitSHA, "runtimeSHA256": art.RuntimeSHA, "initBytes": art.InitBytes, "runtimeBytes": art.RuntimeBytes,'
new = '"compiler": art.Compiler.Version, "sourceSHA256": art.SourceSHA, "initSHA256": art.InitSHA, "runtimeSHA256": art.RuntimeSHA, "initBytes": art.InitBytes, "runtimeBytes": art.RuntimeBytes,'
if old not in s:
    raise SystemExit('parent driver report form was not the retained expected form')
target.write_text(s.replace(old, new))
