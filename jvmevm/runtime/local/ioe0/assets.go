// Package ioe0assets embeds the pinned LOCAL EVM IOException runtime.
package ioe0assets

import _ "embed"

//go:embed artifacts/IOException0Interpreter.json
var artifact []byte

// Artifact returns an independent copy so callers cannot alter the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
