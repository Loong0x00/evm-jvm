// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.
//
// go-ethereum is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// go-ethereum is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with go-ethereum. If not, see <http://www.gnu.org/licenses/>.

// javaevm translates the tiny M0 Java int subset and executes it in geth's EVM.
package main

import (
	"encoding/hex"
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/ethereum/go-ethereum/javaevm"
)

func main() {
	classPath := flag.String("class", "", "path to a .class file")
	method := flag.String("method", "add", "static method name")
	argText := flag.String("args", "", "comma-separated signed int32 arguments")
	gas := flag.Uint64("gas", 100000, "EVM gas limit")
	flag.Parse()
	if *classPath == "" || *argText == "" {
		fmt.Fprintln(os.Stderr, "usage: javaevm -class Add.class [-method add] -args 20,22 [-gas 100000]")
		os.Exit(2)
	}
	args, err := parseArgs(*argText)
	if err != nil {
		fatal(err)
	}
	classfile, err := os.ReadFile(*classPath)
	if err != nil {
		fatal(fmt.Errorf("read classfile: %w", err))
	}
	program, err := javaevm.CompileClass(classfile, *method)
	if err != nil {
		fatal(err)
	}
	result, err := javaevm.Run(program, args, *gas)
	if err != nil {
		fmt.Fprintf(os.Stderr, "javaevm: %v (gas_used=%d)\n", err, result.GasUsed)
		os.Exit(1)
	}
	fmt.Printf("bytecode=0x%s\nresult=%d\ngas_used=%d\n", hex.EncodeToString(program.Code), result.Value, result.GasUsed)
}

func parseArgs(s string) ([]int32, error) {
	parts := strings.Split(s, ",")
	args := make([]int32, len(parts))
	for i, part := range parts {
		value, err := strconv.ParseInt(strings.TrimSpace(part), 10, 32)
		if err != nil {
			return nil, fmt.Errorf("argument %d is not a signed int32: %q", i+1, part)
		}
		args[i] = int32(value)
	}
	return args, nil
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "javaevm:", err)
	os.Exit(1)
}
