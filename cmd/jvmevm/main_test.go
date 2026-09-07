// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package main

import (
	"testing"

	"github.com/ethereum/go-ethereum/jvmevm"
)

func TestFormatOutcomeUsesExactlyOneOutcomeKey(t *testing.T) {
	if got := formatOutcome(jvmevm.Result{Value: -7}); got != "result=-7" {
		t.Fatalf("value outcome = %q", got)
	}
	if got := formatOutcome(jvmevm.Result{ExceptionClass: "java.lang.ArithmeticException"}); got != "exception=java.lang.ArithmeticException" {
		t.Fatalf("exception outcome = %q", got)
	}
}
