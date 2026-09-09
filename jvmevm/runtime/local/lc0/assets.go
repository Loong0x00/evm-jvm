// Package lc0assets embeds the pinned LOCAL EVM runtime build, not guest state.
package lc0assets

import _ "embed"

//go:embed artifacts/LC0Interpreter.json
var artifact []byte

// Artifact returns an independent copy so callers cannot alter the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
