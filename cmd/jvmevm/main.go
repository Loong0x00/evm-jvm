// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

// jvmevm sends unchanged classfiles to a generic JVM-subset interpreter
// implemented in EVM bytecode. It never parses, links, or translates Java on the host.
package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/ethereum/go-ethereum/jvmevm"
)

type classPaths []string

func (p *classPaths) String() string { return strings.Join(*p, ",") }
func (p *classPaths) Set(value string) error {
	*p = append(*p, value)
	return nil
}

func main() {
	var classes classPaths
	flag.Var(&classes, "class", "path to an unchanged javac .class file (repeat for bundles)")
	entryClass := flag.String("entry-class", "", "explicit JVM internal entry class name for bundle mode")
	method := flag.String("method", "", "unambiguous static method name")
	argText := flag.String("args", "", "comma-separated signed int32 arguments")
	gas := flag.Uint64("gas", 2_000_000, "EVM gas limit")
	flag.Parse()
	if len(classes) == 0 || *method == "" || (len(classes) > 1 && *entryClass == "") {
		fmt.Fprintln(os.Stderr, "usage: jvmevm -class Add.class [-class Helper.class -entry-class pkg/Add] -method add [-args 20,22] [-gas 2000000]")
		os.Exit(2)
	}
	args, err := parseArgs(*argText)
	if err != nil {
		fatal(err)
	}
	classfiles := make([][]byte, len(classes))
	for i, path := range classes {
		classfiles[i], err = os.ReadFile(path)
		if err != nil {
			fatal(fmt.Errorf("read raw classfile %q: %w", path, err))
		}
	}
	var result jvmevm.Result
	if *entryClass == "" {
		result, err = jvmevm.Run(classfiles[0], *method, args, *gas)
	} else {
		result, err = jvmevm.RunClasses(classfiles, *entryClass, *method, args, *gas)
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "jvmevm: %v (gas_used=%d runtime_sha256=%s)\n", err, result.GasUsed, result.RuntimeSHA256)
		os.Exit(1)
	}
	code, err := jvmevm.Runtime()
	if err != nil {
		fatal(err)
	}
	fmt.Printf("engine=evm-jvm-subset-interpreter\nruntime_bytes=%d\nruntime_sha256=%s\n%s\ngas_used=%d\n", len(code), result.RuntimeSHA256, formatOutcome(result), result.GasUsed)
}

func formatOutcome(result jvmevm.Result) string {
	if result.ExceptionClass != "" {
		return "exception=" + result.ExceptionClass
	}
	return fmt.Sprintf("result=%d", result.Value)
}

func parseArgs(s string) ([]int32, error) {
	if strings.TrimSpace(s) == "" {
		return []int32{}, nil
	}
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
	fmt.Fprintln(os.Stderr, "jvmevm:", err)
	os.Exit(1)
}
