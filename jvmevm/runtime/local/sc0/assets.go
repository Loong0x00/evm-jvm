// Package sc0assets embeds the pinned LOCAL EVM String runtime, not guest state.
package sc0assets

import _ "embed"

//go:embed artifacts/String0Interpreter.json
var artifact []byte

// Artifact returns an independent copy so callers cannot alter the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
