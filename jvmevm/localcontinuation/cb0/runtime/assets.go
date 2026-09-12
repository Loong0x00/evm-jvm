// Package runtimeassets embeds the pinned MC-CB0 coordinator build artifact.
package runtimeassets

import _ "embed"

//go:embed combinedartifacts/CB0ClassCoordinator.json
var artifact []byte

// Artifact returns an independent copy so callers cannot mutate the embedded input.
func Artifact() []byte { return append([]byte(nil), artifact...) }
