// Package tl0assets embeds the pinned LOCAL EVM Throwable runtime build, not guest state.
package tl0assets

import _ "embed"

//go:embed artifacts/Throwable0Interpreter.json
var artifact []byte

// Artifact returns an independent copy so callers cannot alter the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
