// Source-only bootstrap root calculator; never executes guest class bytes.
package main

import (
	"bufio"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"

	"golang.org/x/crypto/sha3"
)

type request struct {
	Domain string     `json:"domain"`
	Pairs  [][]string `json:"pairs"`
}

func keccak(data []byte) []byte {
	h := sha3.NewLegacyKeccak256()
	_, _ = h.Write(data)
	return h.Sum(nil)
}

func word(n uint64) []byte {
	out := make([]byte, 32)
	for i := 0; i < 8; i++ {
		out[31-i] = byte(n >> (8 * i))
	}
	return out
}

func main() {
	b, err := io.ReadAll(bufio.NewReader(os.Stdin))
	if err != nil {
		panic(err)
	}
	var in request
	if err = json.Unmarshal(b, &in); err != nil {
		panic(err)
	}
	if len(in.Pairs) != 97 {
		panic("expected exactly 97 ordered leaves")
	}
	leaves := make([][]byte, len(in.Pairs))
	for i, pair := range in.Pairs {
		if len(pair) != 2 {
			panic("malformed pair")
		}
		v, err := hex.DecodeString(pair[1])
		if err != nil {
			panic(err)
		}
		switch pair[0] {
		case "image":
			leaves[i] = keccak(v)
		case "hexhash":
			if len(v) != 32 {
				panic("non-bytes32 hash")
			}
			leaves[i] = v
		default:
			panic("unknown leaf kind")
		}
	}
	buf := append(keccak([]byte(in.Domain)), word(64)...)
	buf = append(buf, word(97)...)
	for _, leaf := range leaves {
		buf = append(buf, leaf...)
	}
	hashes := make([]string, len(leaves))
	for i, leaf := range leaves {
		hashes[i] = hex.EncodeToString(leaf)
	}
	out := struct {
		Root   string   `json:"root"`
		Leaves []string `json:"leaves"`
	}{hex.EncodeToString(keccak(buf)), hashes}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(out); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
