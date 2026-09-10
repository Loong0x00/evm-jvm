// Package runtimeassets embeds the pinned MC-ZI0 controller build artifact.
package runtimeassets

import _ "embed"

//go:embed combinedartifacts/ZI0ZipIndex.json
var artifact []byte

// Artifact returns an independent copy so callers cannot mutate the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
