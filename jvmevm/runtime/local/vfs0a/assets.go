// Package vfs0aassets embeds the measured LOCAL EVM VFS0a runtime candidate.
package vfs0aassets

import _ "embed"

//go:embed artifacts/VFS0aInterpreter.json
var artifact []byte

// Artifact returns an independent copy so callers cannot alter the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
