// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"encoding/binary"
	"errors"
	"fmt"
	"math"
	"strconv"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
)

const (
	verifyM5caGasLimit     = uint64(180_000_000)
	verifyM5caLoopGasLimit = uint64(500_000)
)

// These verifier-only probes use bounded trusted Java 8 classes. Raw mutations
// which are valid classfiles are checked with a real Java 8 VM; malformed Code
// structures are EVM predecoder probes, not claims of complete classfile
// verification. Production continues to receive only opaque classfile bytes.

type verifyM5caSwitch struct {
	code        []byte
	opPC        int
	headerPC    int
	offsetWords []int // default first, then case/pair offsets
	targetPCs   []int // in the same order as offsetWords
}

func TestVerifyM5caTableAndLookupSwitchAlignmentSignedKeysAndPadding(t *testing.T) {
	base := verifyM5caRawFixture(t, 900)
	for alignment := 0; alignment < 4; alignment++ {
		t.Run(fmt.Sprintf("tableswitch-align-%d", alignment), func(t *testing.T) {
			sw := verifyM5caTableSwitch(t, alignment, -1, 1, []int32{11, 22, 33}, 44)
			verifyM5caRequireDecodedOpcode(t, sw.code, sw.opPC, 0xaa)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", sw.code, 2, 1)
			nonzero := verifyM5caNonzeroSwitchPadding(t, sw)
			nonzeroClass := verifyM5caRewrite(t, base, "padding", "(I)I", nonzero, 2, 1)
			for _, tc := range []struct{ arg, want int32 }{{-1, 11}, {0, 22}, {1, 33}, {-2, 44}, {2, 44}} {
				// HotSpot 8 is the oracle for the ordinary valid raw form. The
				// spec-valid nonzero padding mutation is exercised independently.
				verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{tc.arg}, tc.want)
				verifyM5caAssertValue(t, nonzeroClass, "padding", []int32{tc.arg}, tc.want)
			}
		})

		t.Run(fmt.Sprintf("lookupswitch-align-%d", alignment), func(t *testing.T) {
			sw := verifyM5caLookupSwitch(t, alignment, []int32{-9, 0, 17}, []int32{51, 52, 53}, 54)
			verifyM5caRequireDecodedOpcode(t, sw.code, sw.opPC, 0xab)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", sw.code, 2, 1)
			nonzero := verifyM5caNonzeroSwitchPadding(t, sw)
			nonzeroClass := verifyM5caRewrite(t, base, "padding", "(I)I", nonzero, 2, 1)
			for _, tc := range []struct{ arg, want int32 }{{-9, 51}, {0, 52}, {17, 53}, {-8, 54}, {18, 54}} {
				verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{tc.arg}, tc.want)
				verifyM5caAssertValue(t, nonzeroClass, "padding", []int32{tc.arg}, tc.want)
			}
		})
	}

	for _, tc := range []struct {
		name      string
		low, high int32
		keys      []int32
		want      []int32
	}{
		{"minimum", math.MinInt32, math.MinInt32 + 1, []int32{math.MinInt32, math.MinInt32 + 1, 0}, []int32{61, 62, 63}},
		{"maximum", math.MaxInt32 - 1, math.MaxInt32, []int32{math.MaxInt32 - 1, math.MaxInt32, -1}, []int32{61, 62, 63}},
	} {
		t.Run("table-signed-"+tc.name, func(t *testing.T) {
			sw := verifyM5caTableSwitch(t, 2, tc.low, tc.high, []int32{61, 62}, 63)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", sw.code, 2, 1)
			for i, key := range tc.keys {
				verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{key}, tc.want[i])
				verifyM5caAssertValue(t, classfile, "padding", []int32{key}, tc.want[i])
			}
		})
	}

	extreme := verifyM5caLookupSwitch(t, 3,
		[]int32{math.MinInt32, -1, math.MaxInt32}, []int32{71, 72, 73}, 74)
	extremeClass := verifyM5caRewrite(t, base, "padding", "(I)I", extreme.code, 2, 1)
	for _, tc := range []struct{ arg, want int32 }{{math.MinInt32, 71}, {-1, 72}, {math.MaxInt32, 73}, {0, 74}} {
		verifyM5caJava8Outcome(t, extremeClass, "VerifyM5caRaw", "padding", []int32{tc.arg}, tc.want)
		verifyM5caAssertValue(t, extremeClass, "padding", []int32{tc.arg}, tc.want)
	}

	empty := verifyM5caLookupSwitch(t, 1, nil, nil, 81)
	emptyClass := verifyM5caRewrite(t, base, "padding", "(I)I", empty.code, 1, 1)
	verifyM5caJava8Outcome(t, emptyClass, "VerifyM5caRaw", "padding", []int32{123}, 81)
	verifyM5caAssertValue(t, emptyClass, "padding", []int32{123}, 81)

	duplicateTarget := verifyM5caLookupSwitch(t, 2, []int32{-3, 9}, []int32{91, 92}, 93)
	verifyM5caPutS4(duplicateTarget.code, duplicateTarget.offsetWords[2],
		int32(duplicateTarget.targetPCs[1]-duplicateTarget.opPC))
	duplicateTarget.targetPCs[2] = duplicateTarget.targetPCs[1]
	duplicateClass := verifyM5caRewrite(t, base, "padding", "(I)I", duplicateTarget.code, 2, 1)
	verifyM5caJava8Outcome(t, duplicateClass, "VerifyM5caRaw", "padding", []int32{9}, 91)
	verifyM5caAssertValue(t, duplicateClass, "padding", []int32{9}, 91)

	// Both switch formats also use signed negative offsets relative to the
	// opcode PC, not to the aligned header or the end of the payload.
	for _, opcode := range []byte{0xaa, 0xab} {
		prefix := []byte{0xa7, 0, 6, 0x10, 99, 0xac, 0x1a}
		var backwards verifyM5caSwitch
		if opcode == 0xaa {
			backwards = verifyM5caAppendTableSwitch(t, prefix, 0, 0, []int32{1}, 2)
		} else {
			backwards = verifyM5caAppendLookupSwitch(t, prefix, []int32{0}, []int32{1}, 2)
		}
		for _, word := range backwards.offsetWords {
			verifyM5caPutS4(backwards.code, word, int32(3-backwards.opPC))
		}
		classfile := verifyM5caRewrite(t, base, "padding", "(I)I", backwards.code, 2, 1)
		verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{0}, 99)
		verifyM5caAssertValue(t, classfile, "padding", []int32{0}, 99)
	}
}

func TestVerifyM5caNonzeroPaddingMajor52SpecAndHotSpotBoundary(t *testing.T) {
	original := verifyM5baCompile(t, map[string]string{
		"VerifyM5caPadding52.java": `public final class VerifyM5caPadding52 {
			public static int table(int x){switch(x){case 0:return 10;case 1:return 11;case 2:return 12;case 3:return 13;default:return 14;}}
			public static int lookup(int x){switch(x){case -100:return 20;case 100:return 21;default:return 22;}}
		}`,
	}, "VerifyM5caPadding52")["VerifyM5caPadding52"]
	if major := binary.BigEndian.Uint16(original[6:8]); major != 52 {
		t.Fatalf("trusted --release 8 probe major=%d want 52", major)
	}

	for _, tc := range []struct {
		method string
		opcode byte
		arg    int32
		want   int32
	}{
		{"table", 0xaa, 1, 11},
		{"lookup", 0xab, 100, 21},
	} {
		t.Run(tc.method, func(t *testing.T) {
			// Preserve the original javac Code, StackMapTable, and major version;
			// mutate only the instruction's alignment padding bytes.
			mutated := append([]byte(nil), original...)
			code := parseStaticsClass(t, mutated).namedMethod(t, tc.method).code
			opPC := verifyM5caInstructionPC(t, code, tc.opcode, 0)
			header := opPC + 1 + (4-((opPC+1)%4))%4
			if header == opPC+1 {
				t.Fatalf("%s switch unexpectedly has no padding", tc.method)
			}
			for pc := opPC + 1; pc < header; pc++ {
				if code[pc] != 0 {
					t.Fatalf("javac %s padding[%d]=0x%02x want zero before mutation", tc.method, pc-opPC-1, code[pc])
				}
				code[pc] = byte(0x70 + pc-opPC)
			}

			verifyM5baJava8Outcome(t, [][]byte{original}, "VerifyM5caPadding52", tc.method,
				[]int32{tc.arg}, "value="+strconv.FormatInt(int64(tc.want), 10))
			// This unchanged-major-52 class retains javac's valid StackMapTable.
			// HotSpot 8 accepts the nonzero bytes, matching SE8 6.5 and 4.9.1's
			// alignment-only rule. This avoids confusing padding with the stale
			// frames in broader raw Code rewrites, which require the major-49
			// old-verifier helper used by malformed-structure probes.
			verifyM5baJava8Outcome(t, [][]byte{mutated}, "VerifyM5caPadding52", tc.method,
				[]int32{tc.arg}, "value="+strconv.FormatInt(int64(tc.want), 10))
			verifyM5caAssertValue(t, mutated, tc.method, []int32{tc.arg}, tc.want)
		})
	}
}

func TestVerifyM5caSwitchPreservesPrefixesAndGuestEffects(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)

	// A category-2 value below the switch key must survive key consumption.
	longPrefix := []byte{0x0a, 0x1a}
	longSwitch := verifyM5caAppendTableSwitch(t, longPrefix, 0, 0, []int32{0}, 0)
	common := len(longSwitch.code)
	longSwitch.code = append(longSwitch.code, 0x88, 0xac) // l2i; ireturn
	for _, word := range longSwitch.offsetWords {
		verifyM5caPutS4(longSwitch.code, word, int32(common-longSwitch.opPC))
	}
	longClass := verifyM5caRewrite(t, base, "padding", "(I)I", longSwitch.code, 3, 1)
	for _, key := range []int32{0, 7} {
		verifyM5caJava8Outcome(t, longClass, "VerifyM5caRaw", "padding", []int32{key}, 1)
		verifyM5caAssertValue(t, longClass, "padding", []int32{key}, 1)
	}

	// A reference below the key is likewise retained. All edges deliberately
	// share one target; duplicate targets are legal even when default aliases it.
	refPrefix := []byte{0x01, 0x1a}
	refSwitch := verifyM5caAppendLookupSwitch(t, refPrefix, []int32{-1, 1}, []int32{0, 0}, 0)
	common = len(refSwitch.code)
	refSwitch.code = append(refSwitch.code, 0x57, 0x08, 0xac) // pop ref; 5; return
	for _, word := range refSwitch.offsetWords {
		verifyM5caPutS4(refSwitch.code, word, int32(common-refSwitch.opPC))
	}
	refClass := verifyM5caRewrite(t, base, "padding", "(I)I", refSwitch.code, 2, 1)
	for _, key := range []int32{-1, 0, 1} {
		verifyM5caJava8Outcome(t, refClass, "VerifyM5caRaw", "padding", []int32{key}, 5)
		verifyM5caAssertValue(t, refClass, "padding", []int32{key}, 5)
	}

	classes := verifyM5baCompile(t, map[string]string{
		"effects/Root.java": `package effects; public final class Root {
			static int state=initialize(); static int initialize(){return 40;} static int helper(int x){return x+state;}
			static final class Box { int x; Box(int x){this.x=x;} }
			public static int dense(int x){int y=0;switch(x){case -1:y=1;break;case 0:y=2;case 1:y+=3;break;case 2:y=6;break;default:y=4;}return helper(y)+new Box(5).x;}
			public static int sparse(int x){switch(x){case -100:return helper(1);case 200:return new Box(helper(2)).x;default:return helper(3);}}
			public static int nestedLoop(int x){int r=0;for(int i=0;i<3;i++){switch(x+i){case -1:r+=1;break;case 0:r+=2;break;default:r+=3;}}switch(r){case 3:return helper(r);case 4:case 5:case 6:return helper(r+2);case 7:return helper(r+1);default:return helper(r+2);}}
		}`,
	}, "effects/Root", "effects/Root$Box")
	root := classes["effects/Root"]
	bundle := verifyM5baBundle(classes)
	denseCode := parseStaticsClass(t, root).namedMethod(t, "dense").code
	sparseCode := parseStaticsClass(t, root).namedMethod(t, "sparse").code
	verifyM5caRequireOpcode(t, denseCode, 0xaa)
	verifyM5caRequireOpcode(t, sparseCode, 0xab)
	nestedCode := parseStaticsClass(t, root).namedMethod(t, "nestedLoop").code
	verifyM5caRequireOpcode(t, nestedCode, 0xaa)
	verifyM5caRequireOpcode(t, nestedCode, 0xab)
	for _, tc := range []struct {
		method string
		arg    int32
		want   int32
	}{
		{"dense", -1, 46}, {"dense", 0, 50}, {"dense", 1, 48}, {"dense", 2, 51}, {"dense", 7, 49},
		{"sparse", -100, 41}, {"sparse", 200, 42}, {"sparse", 0, 43},
		{"nestedLoop", -1, 48}, {"nestedLoop", 5, 51},
	} {
		jvmWant := verifyM5baJava8Int(t, bundle, "effects.Root", tc.method, []int32{tc.arg})
		if jvmWant != tc.want {
			t.Fatalf("JVM %s(%d)=%d want intended fallthrough/effect value %d", tc.method, tc.arg, jvmWant, tc.want)
		}
		verifyM5baAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "effects/Root", tc.method, []int32{tc.arg}, verifyM5caGasLimit)
		}, tc.want)
	}
}

func TestVerifyM5caSwitchMalformedStructuresTruncationAndSafeCounts(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)

	malformed := []struct {
		name string
		code []byte
		opPC int
	}{
		{"table-low-after-high", verifyM5caMalformedTable(1, 8, 7), 1},
		{"lookup-negative-pairs", verifyM5caMalformedLookup(2, -1, nil), 2},
		{"lookup-unsorted", verifyM5caMalformedLookup(3, 2, []int32{7, 0, 6, 0}), 3},
		{"lookup-duplicate-key", verifyM5caMalformedLookup(1, 2, []int32{7, 0, 7, 0}), 1},
	}
	for _, tc := range malformed {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", tc.code, 1, 1)
			verifyM5caAssertBytecodeError(t, classfile, "padding", []int32{0}, 15, tc.opPC)
		})
	}

	// The mathematical counts do not fit the remaining Code. They must become
	// bounded truncation errors, without uint32 wraparound or count-sized allocation.
	hugeTable := verifyM5caMalformedTable(1, math.MinInt32, math.MaxInt32)
	hugeLookup := verifyM5caMalformedLookup(2, math.MaxInt32, nil)
	for _, tc := range []struct {
		name string
		code []byte
		pc   int
	}{{"table-huge-range", hugeTable, 1}, {"lookup-huge-npairs", hugeLookup, 2}} {
		t.Run(tc.name, func(t *testing.T) {
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", tc.code, 1, 1)
			verifyM5caAssertBytecodeError(t, classfile, "padding", []int32{0}, 2, tc.pc)
		})
	}

	truncations := []struct {
		name           string
		opcode         byte
		body           []byte // bytes after complete alignment padding
		includePadding bool
	}{
		{"table-padding", 0xaa, nil, false},
		{"table-header", 0xaa, make([]byte, 11), true},
		{"table-offset", 0xaa, append(append(verifyM5caS4(0), verifyM5caS4(0)...), verifyM5caS4(0)...), true},
		{"lookup-padding", 0xab, nil, false},
		{"lookup-header", 0xab, make([]byte, 7), true},
		{"lookup-pair", 0xab, append(append(verifyM5caS4(0), verifyM5caS4(1)...), make([]byte, 7)...), true},
	}
	// table-offset advertises one entry (low=high=0) but has no entry offset.
	for _, tc := range truncations {
		t.Run(tc.name, func(t *testing.T) {
			code, pc := verifyM5caTruncatedSwitch(tc.opcode, tc.body, tc.includePadding)
			classfile := verifyM5caRewriteExact(t, base, "padding", "(I)I", code, 1, 1)
			verifyM5caAssertBytecodeError(t, classfile, "padding", []int32{0}, 2, pc)
		})
	}
}

func TestVerifyM5caEverySwitchEdgeUsesInstructionBoundaries(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)
	for _, kind := range []byte{0xaa, 0xab} {
		name := "table"
		var sw verifyM5caSwitch
		if kind == 0xaa {
			sw = verifyM5caTableSwitch(t, 1, -1, 1, []int32{11, 12, 13}, 14)
		} else {
			name = "lookup"
			sw = verifyM5caLookupSwitch(t, 1, []int32{-1, 0, 1}, []int32{11, 12, 13}, 14)
		}
		// Add a valid wide instruction in otherwise unreachable trailing Code.
		widePC := len(sw.code)
		sw.code = append(sw.code, 0xc4, 0x15, 0x00, 0x00, 0x57)
		verifyM5caRequireDecodedOpcode(t, sw.code, widePC, 0xc4)
		codeLimit := len(parseStaticsClass(t, base).method(t, "padding", "(I)I").code)
		nonStarts := []int{sw.opPC + 1, sw.headerPC, sw.offsetWords[0] + 1, widePC + 1, -1, codeLimit}
		for edge := range sw.offsetWords { // includes default and every unselected edge
			for i, target := range nonStarts {
				t.Run(fmt.Sprintf("%s-edge-%d-nonstart-%d", name, edge, i), func(t *testing.T) {
					badCode := append([]byte(nil), sw.code...)
					verifyM5caPutS4(badCode, sw.offsetWords[edge], int32(target-sw.opPC))
					bad := verifyM5caRewrite(t, base, "padding", "(I)I", badCode, 2, 1)
					// Select key zero. Most mutated edges, including default, are untaken.
					verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 12, sw.opPC)
				})
			}
		}
	}
}

func TestVerifyM5caSwitchKeyKindsUnderflowAndErrorPC(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)
	selfIndex := parseStaticsClass(t, base).thisClass
	prefixes := []struct {
		name   string
		prefix []byte
		kind   uint64
	}{
		{"absent", nil, 3},
		{"null-reference", []byte{0x01}, 14},
		{"long", []byte{0x09}, 14},
		{"uninitialized-reference", []byte{0xbb, byte(selfIndex >> 8), byte(selfIndex)}, 14},
		{"int-below-long", []byte{0x03, 0x09}, 14},
	}
	for _, opcode := range []byte{0xaa, 0xab} {
		for _, tc := range prefixes {
			t.Run(fmt.Sprintf("%02x-%s", opcode, tc.name), func(t *testing.T) {
				var sw verifyM5caSwitch
				if opcode == 0xaa {
					sw = verifyM5caAppendTableSwitch(t, tc.prefix, 0, 0, []int32{1}, 1)
				} else {
					sw = verifyM5caAppendLookupSwitch(t, tc.prefix, nil, nil, 1)
				}
				bad := verifyM5caRewrite(t, base, "padding", "(I)I", sw.code, 4, 1)
				verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, tc.kind, sw.opPC)
			})
		}
	}
}

func TestVerifyM5caGotoWLongDistancesBackwardAndPrefixPreservation(t *testing.T) {
	base := verifyM5caRawFixture(t, 14_000)
	methodLen := len(parseStaticsClass(t, base).method(t, "padding", "(I)I").code)
	if methodLen <= 40_020 {
		t.Fatalf("long-distance raw fixture Code length=%d want >40020", methodLen)
	}

	forward := make([]byte, 40_004)
	forward[0] = 0xc8
	verifyM5caPutS4(forward, 1, 40_000)
	forward[40_000], forward[40_001], forward[40_002] = 0x10, 42, 0xac
	verifyM5caRequireDecodedOpcode(t, forward, 0, 0xc8)
	verifyM5caRequireDecodedOpcode(t, forward, 40_000, 0x10)
	forwardClass := verifyM5caRewrite(t, base, "padding", "(I)I", forward, 1, 1)
	verifyM5caJava8Outcome(t, forwardClass, "VerifyM5caRaw", "padding", []int32{0}, 42)

	backward := make([]byte, 40_010)
	backward[0], backward[1] = 0x03, 0x3b // local 0 = 0
	target := 2
	backward[target] = 0x1a
	backward[target+1] = 0x9a
	binary.BigEndian.PutUint16(backward[target+2:], 8) // return at PC 11
	forwardPC := 6
	backward[forwardPC] = 0xc8
	verifyM5caPutS4(backward, forwardPC+1, int32(40_000-forwardPC))
	backward[11], backward[12] = 0x1a, 0xac
	backward[40_000], backward[40_001], backward[40_002] = 0x84, 0, 1
	backPC := 40_003
	backward[backPC] = 0xc8
	verifyM5caPutS4(backward, backPC+1, int32(target-backPC))
	if delta := target - backPC; delta >= -32767 {
		t.Fatalf("backward goto_w delta=%d is not wider than int16", delta)
	}
	backClass := verifyM5caRewrite(t, base, "padding", "(I)I", backward, 1, 1)
	verifyM5caJava8Outcome(t, backClass, "VerifyM5caRaw", "padding", []int32{0}, 1)
	verifyM5caAssertValue(t, forwardClass, "padding", []int32{0}, 42)
	verifyM5caAssertValue(t, backClass, "padding", []int32{0}, 1)

	for _, tc := range []struct {
		name   string
		prefix []byte
		tail   []byte
		want   int32
	}{
		{"long", []byte{0x0a}, []byte{0x88, 0xac}, 1},
		{"reference", []byte{0x01}, []byte{0x57, 0x07, 0xac}, 4},
	} {
		t.Run("prefix-"+tc.name, func(t *testing.T) {
			code := append([]byte(nil), tc.prefix...)
			gotoPC := len(code)
			code = append(code, 0xc8, 0, 0, 0, 0, 0, 0, 0)
			targetPC := len(code)
			code = append(code, tc.tail...)
			verifyM5caPutS4(code, gotoPC+1, int32(targetPC-gotoPC))
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", code, 3, 1)
			verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{0}, tc.want)
			verifyM5caAssertValue(t, classfile, "padding", []int32{0}, tc.want)
		})
	}
}

func TestVerifyM5caGotoWTargetsPayloadWideOperandAndSelfLoopOOG(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)
	// Keep the switch at its actual final PC: alignment is method-relative and
	// must not be reused after blindly prepending bytes.
	sw := verifyM5caAppendTableSwitch(t, []byte{0xc8, 0, 0, 0, 0, 0x03}, 0, 0, []int32{1}, 2)
	widePC := len(sw.code)
	sw.code = append(sw.code, 0xc4, 0x15, 0, 0, 0x57)
	codeLimit := len(parseStaticsClass(t, base).method(t, "padding", "(I)I").code)
	for _, target := range []int{sw.opPC + 1, sw.headerPC, sw.offsetWords[1], widePC + 1, -1, codeLimit} {
		t.Run(fmt.Sprintf("target-%d", target), func(t *testing.T) {
			code := append([]byte(nil), sw.code...)
			verifyM5caPutS4(code, 1, int32(target))
			bad := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1)
			verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 12, 0)
		})
	}

	loop := verifyM5caRewrite(t, base, "padding", "(I)I", []byte{0xc8, 0, 0, 0, 0}, 0, 1)
	result, err := Run(loop, "padding", []int32{0}, verifyM5caLoopGasLimit)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.GasUsed != verifyM5caLoopGasLimit ||
		result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("self goto_w result/error=%+v/%v want finite unlabeled EVM OOG", result, err)
	}
}

func TestVerifyM5caWideUnsignedIndicesLongBoundsReferencesAndIinc(t *testing.T) {
	base := verifyM5caRawFixture(t, 900)
	for _, index := range []uint16{255, 256, 1023} {
		t.Run(fmt.Sprintf("int-index-%d", index), func(t *testing.T) {
			code := []byte{0x10, 37}
			code = append(code, verifyM5caWide(0x36, index)...)
			code = append(code, verifyM5caWide(0x15, index)...)
			code = append(code, 0xac)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", code, 1, 1024)
			verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{0}, 37)
			verifyM5caAssertValue(t, classfile, "padding", []int32{0}, 37)
		})
	}
	for _, index := range []uint16{255, 1022} {
		t.Run(fmt.Sprintf("long-index-%d", index), func(t *testing.T) {
			code := []byte{0x0a}
			code = append(code, verifyM5caWide(0x37, index)...)
			code = append(code, verifyM5caWide(0x16, index)...)
			code = append(code, 0x88, 0xac)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1024)
			verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{0}, 1)
			verifyM5caAssertValue(t, classfile, "padding", []int32{0}, 1)
		})
	}

	for _, tc := range []struct {
		name  string
		start int32
		delta int16
		want  int32
	}{
		{"min-delta", 0, math.MinInt16, math.MinInt16},
		{"max-delta", 0, math.MaxInt16, math.MaxInt16},
		{"positive-overflow", math.MaxInt32, 1, math.MinInt32},
		{"negative-overflow", math.MinInt32, -1, math.MaxInt32},
	} {
		t.Run("iinc-"+tc.name, func(t *testing.T) {
			code := []byte{0x1a}
			code = append(code, verifyM5caWide(0x36, 256)...)
			code = append(code, verifyM5caWideIinc(256, tc.delta)...)
			code = append(code, verifyM5caWide(0x15, 256)...)
			code = append(code, 0xac)
			classfile := verifyM5caRewrite(t, base, "padding", "(I)I", code, 1, 257)
			verifyM5caJava8Outcome(t, classfile, "VerifyM5caRaw", "padding", []int32{tc.start}, tc.want)
			verifyM5caAssertValue(t, classfile, "padding", []int32{tc.start}, tc.want)
		})
	}

	// astore/aload retain typed null references at high unsigned indices.
	refCode := []byte{0x01}
	refCode = append(refCode, verifyM5caWide(0x3a, 256)...)
	refCode = append(refCode, verifyM5caWide(0x19, 256)...)
	refCode = append(refCode, 0xc6, 0, 5, 0x03, 0xac, 0x04, 0xac)
	refClass := verifyM5caRewrite(t, base, "padding", "(I)I", refCode, 1, 257)
	verifyM5caJava8Outcome(t, refClass, "VerifyM5caRaw", "padding", []int32{0}, 1)
	verifyM5caAssertValue(t, refClass, "padding", []int32{0}, 1)
}

func TestVerifyM5caWideUninitializedReferenceAliasesAndOverlapInvalidation(t *testing.T) {
	compiled := verifyM5baCompile(t, map[string]string{
		"VerifyM5caObject.java": `public final class VerifyM5caObject {
			public VerifyM5caObject(){} public static int object(){VerifyM5caObject x=new VerifyM5caObject();return x==null?0:1;}
			public static int padding(int x){` + strings.Repeat("x=x+1;", 500) + `return x;}
		}`,
	}, "VerifyM5caObject")["VerifyM5caObject"]
	objectCode := parseStaticsClass(t, compiled).namedMethod(t, "object").code
	newPC := verifyM5caInstructionPC(t, objectCode, 0xbb, 0)
	initPC := verifyM5caInstructionPC(t, objectCode, 0xb7, 0)
	classIndex := binary.BigEndian.Uint16(objectCode[newPC+1:])
	constructorIndex := binary.BigEndian.Uint16(objectCode[initPC+1:])
	code := []byte{0xbb, byte(classIndex >> 8), byte(classIndex)}
	code = append(code, verifyM5caWide(0x3a, 256)...)
	code = append(code, verifyM5caWide(0x19, 256)...)
	code = append(code, 0xb7, byte(constructorIndex>>8), byte(constructorIndex))
	code = append(code, verifyM5caWide(0x19, 256)...)
	code = append(code, 0x57, 0x04, 0xac)
	valid := verifyM5caRewrite(t, compiled, "padding", "(I)I", code, 1, 257)
	verifyM5caJava8Outcome(t, valid, "VerifyM5caObject", "padding", []int32{0}, 1)
	verifyM5caAssertValue(t, valid, "padding", []int32{0}, 1)

	base := verifyM5caRawFixture(t, 500)
	invalid := []struct {
		name string
		code []byte
		max  uint16
		kind uint64
		pc   int
	}{
		{"lload-1023-range", append(verifyM5caWide(0x16, 1023), 0x88, 0xac), 1024, 8, 0},
		{"lstore-1023-range", append([]byte{0x0a}, append(verifyM5caWide(0x37, 1023), 0x03, 0xac)...), 1024, 8, 1},
		{"iload-1024-range", append(verifyM5caWide(0x15, 1024), 0xac), 1024, 8, 0},
		{"uninitialized-int", append(verifyM5caWide(0x15, 256), 0xac), 257, 11, 0},
		{"long-head-as-int", append(append([]byte{0x0a}, verifyM5caWide(0x37, 255)...), append(verifyM5caWide(0x15, 255), 0xac)...), 257, 14, 5},
		{"long-tail-as-int", append(append([]byte{0x0a}, verifyM5caWide(0x37, 255)...), append(verifyM5caWide(0x15, 256), 0xac)...), 257, 14, 5},
		{"istore-overwrites-head", verifyM5caOverlapCode(255, 255), 257, 14, 10},
		{"istore-overwrites-tail", verifyM5caOverlapCode(255, 256), 257, 11, 10},
		{"astore-overwrites-head", verifyM5caReferenceOverlapCode(255, 255), 257, 14, 10},
		{"astore-overwrites-tail", verifyM5caReferenceOverlapCode(255, 256), 257, 11, 10},
		{"lstore-overlaps-left", verifyM5caLongOverlapCode(255, 254), 257, 14, 10},
		{"lstore-overlaps-right", verifyM5caLongOverlapCode(255, 256), 258, 11, 10},
		{"iinc-long-head", verifyM5caIincLongCode(255), 257, 14, 5},
		{"iinc-long-tail", verifyM5caIincLongCode(256), 257, 14, 5},
	}
	for _, tc := range invalid {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM5caRewrite(t, base, "padding", "(I)I", tc.code, 3, tc.max)
			verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, tc.kind, tc.pc)
		})
	}

	tooManyLocals := verifyM5caRewrite(t, base, "padding", "(I)I", []byte{0x1a, 0xac}, 1, 1025)
	verifyM5caAssertBytecodeError(t, tooManyLocals, "padding", []int32{0}, 10, 0)
}

func TestVerifyM5caWideUnsupportedInvalidFormsAndTruncationUsePrefixPC(t *testing.T) {
	base := verifyM5caRawFixture(t, 500)
	// M5c-b supports wide F/D load/store. With the existing int argument in
	// local 0, and max_locals=1, these isolate kind, index, and stack faults.
	for _, tc := range []struct {
		embedded byte
		kind     uint64
	}{
		{0x17, 14}, // fload sees initialized int
		{0x18, 8},  // dload needs local 0 plus tail slot
		{0x38, 3},  // fstore has no operand
		{0x39, 8},  // dstore range validation precedes operand validation
	} {
		t.Run(fmt.Sprintf("wide-fp-fault-%02x", tc.embedded), func(t *testing.T) {
			code := append(verifyM5caWide(tc.embedded, 0), 0x03, 0xac)
			bad := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1)
			verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, tc.kind, 0)
		})
	}
	t.Run("unsupported-wide-ret", func(t *testing.T) {
		code := append(verifyM5caWide(0xa9, 0), 0x03, 0xac)
		bad := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1)
		verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 6, 0)
	})
	for _, embedded := range []byte{0x00, 0x1a, 0x60, 0xc4, 0xc8, 0xaa, 0xab} {
		t.Run(fmt.Sprintf("invalid-%02x", embedded), func(t *testing.T) {
			code := append(verifyM5caWide(embedded, 0), 0x03, 0xac)
			bad := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1)
			verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 15, 0)
		})
	}
	for _, opcode := range []byte{0xa8, 0xa9, 0xc9} { // jsr, ret, jsr_w remain deferred
		t.Run(fmt.Sprintf("deferred-%02x", opcode), func(t *testing.T) {
			width := 1
			if opcode == 0xa8 {
				width = 3
			} else if opcode == 0xc9 {
				width = 5
			}
			code := append(make([]byte, width), 0x03, 0xac)
			code[0] = opcode
			bad := verifyM5caRewrite(t, base, "padding", "(I)I", code, 2, 1)
			verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 6, 0)
		})
	}

	codeLen := len(parseStaticsClass(t, base).method(t, "padding", "(I)I").code)
	for length := 1; length < 4; length++ { // supported wide load/store has total width four
		ending := []byte{0xc4}
		if length >= 2 {
			ending = append(ending, 0x15)
		}
		ending = append(ending, make([]byte, length-len(ending))...)
		bad := verifyM5baRewriteAtEnd(t, base, "padding", "(I)I", ending)
		verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 2, codeLen-len(ending))
	}
	for length := 2; length < 6; length++ { // wide iinc has total width six
		ending := append([]byte{0xc4, 0x84}, make([]byte, length-2)...)
		bad := verifyM5baRewriteAtEnd(t, base, "padding", "(I)I", ending)
		verifyM5caAssertBytecodeError(t, bad, "padding", []int32{0}, 2, codeLen-len(ending))
	}
}

// --- M5c-a verifier-only helpers ---

func verifyM5caRawFixture(t *testing.T, increments int) []byte {
	t.Helper()
	source := `public final class VerifyM5caRaw {
		public static int padding(int x){` + strings.Repeat("x=x+1;", increments) + `return x;}
	}`
	return verifyM5baCompile(t, map[string]string{"VerifyM5caRaw.java": source}, "VerifyM5caRaw")["VerifyM5caRaw"]
}

func verifyM5caRewrite(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	return verifyM5baRewriteCode(t, original, name, descriptor, code, maxStack, maxLocals)
}

func verifyM5caSwitchPrefix(alignment int) []byte {
	if alignment < 0 || alignment > 3 {
		panic("invalid switch alignment")
	}
	opPC := alignment
	if opPC == 0 {
		opPC = 4
	}
	code := make([]byte, opPC)
	code[opPC-1] = 0x1a // iload_0 is derived as the instruction before the switch
	return code
}

func verifyM5caTableSwitch(t *testing.T, alignment int, low, high int32, values []int32, defaultValue int32) verifyM5caSwitch {
	t.Helper()
	return verifyM5caAppendTableSwitch(t, verifyM5caSwitchPrefix(alignment), low, high, values, defaultValue)
}

func verifyM5caAppendTableSwitch(t *testing.T, prefix []byte, low, high int32, values []int32, defaultValue int32) verifyM5caSwitch {
	t.Helper()
	if int64(high)-int64(low)+1 != int64(len(values)) || low > high {
		t.Fatalf("bad test tableswitch range %d..%d for %d values", low, high, len(values))
	}
	code := append([]byte(nil), prefix...)
	opPC := len(code)
	code = append(code, 0xaa)
	for len(code)%4 != 0 {
		code = append(code, 0)
	}
	header := len(code)
	defaultWord := len(code)
	code = append(code, make([]byte, 4)...)
	code = append(code, verifyM5caS4(low)...)
	code = append(code, verifyM5caS4(high)...)
	offsetWords := []int{defaultWord}
	for range values {
		offsetWords = append(offsetWords, len(code))
		code = append(code, make([]byte, 4)...)
	}
	targets := make([]int, 1+len(values))
	for i, value := range values {
		targets[i+1] = len(code)
		code = append(code, 0x10, byte(value), 0xac)
	}
	targets[0] = len(code)
	code = append(code, 0x10, byte(defaultValue), 0xac)
	for i := range offsetWords {
		verifyM5caPutS4(code, offsetWords[i], int32(targets[i]-opPC))
	}
	return verifyM5caSwitch{code: code, opPC: opPC, headerPC: header, offsetWords: offsetWords, targetPCs: targets}
}

func verifyM5caLookupSwitch(t *testing.T, alignment int, keys, values []int32, defaultValue int32) verifyM5caSwitch {
	t.Helper()
	return verifyM5caAppendLookupSwitch(t, verifyM5caSwitchPrefix(alignment), keys, values, defaultValue)
}

func verifyM5caAppendLookupSwitch(t *testing.T, prefix []byte, keys, values []int32, defaultValue int32) verifyM5caSwitch {
	t.Helper()
	if len(keys) != len(values) {
		t.Fatalf("bad lookup fixture keys=%d values=%d", len(keys), len(values))
	}
	for i := 1; i < len(keys); i++ {
		if keys[i-1] >= keys[i] {
			t.Fatalf("valid lookup fixture keys are not strictly increasing: %v", keys)
		}
	}
	code := append([]byte(nil), prefix...)
	opPC := len(code)
	code = append(code, 0xab)
	for len(code)%4 != 0 {
		code = append(code, 0)
	}
	header := len(code)
	defaultWord := len(code)
	code = append(code, make([]byte, 4)...)
	code = append(code, verifyM5caS4(int32(len(keys)))...)
	offsetWords := []int{defaultWord}
	for _, key := range keys {
		code = append(code, verifyM5caS4(key)...)
		offsetWords = append(offsetWords, len(code))
		code = append(code, make([]byte, 4)...)
	}
	targets := make([]int, 1+len(values))
	for i, value := range values {
		targets[i+1] = len(code)
		code = append(code, 0x10, byte(value), 0xac)
	}
	targets[0] = len(code)
	code = append(code, 0x10, byte(defaultValue), 0xac)
	for i := range offsetWords {
		verifyM5caPutS4(code, offsetWords[i], int32(targets[i]-opPC))
	}
	return verifyM5caSwitch{code: code, opPC: opPC, headerPC: header, offsetWords: offsetWords, targetPCs: targets}
}

func verifyM5caNonzeroSwitchPadding(t *testing.T, sw verifyM5caSwitch) []byte {
	t.Helper()
	out := append([]byte(nil), sw.code...)
	for pc := sw.opPC + 1; pc < sw.headerPC; pc++ {
		out[pc] = byte(0x70 + pc%16)
	}
	// Alignment 3 has no padding. Across the four alignment subtests, the
	// other forms cover one, two, and three ignored nonzero bytes.
	return out
}

func verifyM5caMalformedTable(opPC int, low, high int32) []byte {
	code := make([]byte, opPC)
	code[opPC-1] = 0x03
	code = append(code, 0xaa)
	for len(code)%4 != 0 {
		code = append(code, 0x7f)
	}
	code = append(code, verifyM5caS4(0)...)
	code = append(code, verifyM5caS4(low)...)
	code = append(code, verifyM5caS4(high)...)
	return code
}

func verifyM5caMalformedLookup(opPC int, npairs int32, words []int32) []byte {
	code := make([]byte, opPC)
	code[opPC-1] = 0x03
	code = append(code, 0xab)
	for len(code)%4 != 0 {
		code = append(code, 0x7e)
	}
	code = append(code, verifyM5caS4(0)...)
	code = append(code, verifyM5caS4(npairs)...)
	for _, word := range words {
		code = append(code, verifyM5caS4(word)...)
	}
	return code
}

func verifyM5caTruncatedSwitch(opcode byte, body []byte, includePadding bool) ([]byte, int) {
	code := []byte{0x03, opcode} // key at PC 0, switch at PC 1 requires two padding bytes
	if includePadding {
		code = append(code, 0, 0)
	}
	code = append(code, body...)
	return code, 1
}

func verifyM5caRewriteExact(t *testing.T, original []byte, name, descriptor string, code []byte, maxStack, maxLocals uint16) []byte {
	t.Helper()
	method := parseStaticsClass(t, original).method(t, name, descriptor)
	start := verifyM5baCodeStart(t, original, method)
	oldLength := len(method.code)
	if len(code) > oldLength {
		t.Fatalf("exact replacement has %d bytes, old Code has %d", len(code), oldLength)
	}
	out := make([]byte, 0, len(original)-oldLength+len(code))
	out = append(out, original[:start]...)
	out = append(out, code...)
	out = append(out, original[start+oldLength:]...)
	binary.BigEndian.PutUint16(out[start-8:], maxStack)
	binary.BigEndian.PutUint16(out[start-6:], maxLocals)
	binary.BigEndian.PutUint32(out[start-4:], uint32(len(code)))
	oldAttributeLength := binary.BigEndian.Uint32(original[start-12:])
	binary.BigEndian.PutUint32(out[start-12:], oldAttributeLength-uint32(oldLength-len(code)))
	return out
}

func verifyM5caS4(value int32) []byte {
	out := make([]byte, 4)
	binary.BigEndian.PutUint32(out, uint32(value))
	return out
}

func verifyM5caPutS4(code []byte, offset int, value int32) {
	binary.BigEndian.PutUint32(code[offset:offset+4], uint32(value))
}

func verifyM5caWide(op byte, index uint16) []byte {
	return []byte{0xc4, op, byte(index >> 8), byte(index)}
}

func verifyM5caWideIinc(index uint16, delta int16) []byte {
	return []byte{0xc4, 0x84, byte(index >> 8), byte(index), byte(uint16(delta) >> 8), byte(delta)}
}

func verifyM5caOverlapCode(longIndex, intIndex uint16) []byte {
	code := []byte{0x0a}
	code = append(code, verifyM5caWide(0x37, longIndex)...)
	code = append(code, 0x04)
	code = append(code, verifyM5caWide(0x36, intIndex)...)
	code = append(code, verifyM5caWide(0x16, longIndex)...)
	code = append(code, 0x88, 0xac)
	return code
}

func verifyM5caReferenceOverlapCode(longIndex, refIndex uint16) []byte {
	code := []byte{0x0a}
	code = append(code, verifyM5caWide(0x37, longIndex)...)
	code = append(code, 0x01)
	code = append(code, verifyM5caWide(0x3a, refIndex)...)
	code = append(code, verifyM5caWide(0x16, longIndex)...)
	code = append(code, 0x88, 0xac)
	return code
}

func verifyM5caLongOverlapCode(first, second uint16) []byte {
	code := []byte{0x0a}
	code = append(code, verifyM5caWide(0x37, first)...)
	code = append(code, 0x0a)
	code = append(code, verifyM5caWide(0x37, second)...)
	code = append(code, verifyM5caWide(0x16, first)...)
	code = append(code, 0x88, 0xac)
	return code
}

func verifyM5caIincLongCode(index uint16) []byte {
	code := []byte{0x0a}
	code = append(code, verifyM5caWide(0x37, 255)...)
	code = append(code, verifyM5caWideIinc(index, 1)...)
	code = append(code, 0x03, 0xac)
	return code
}

func verifyM5caJava8Outcome(t *testing.T, classfile []byte, className, method string, args []int32, want int32) {
	t.Helper()
	verifyM5baJava8Outcome(t, [][]byte{verifyM5baMajor49(classfile)}, className, method, args,
		"value="+strconv.FormatInt(int64(want), 10))
}

func verifyM5caAssertValue(t *testing.T, classfile []byte, method string, args []int32, want int32) {
	t.Helper()
	verifyM5baAssertValue(t, func() (Result, error) {
		return Run(classfile, method, args, verifyM5caGasLimit)
	}, want)
}

func verifyM5caAssertBytecodeError(t *testing.T, classfile []byte, method string, args []int32, code uint64, pc int) {
	t.Helper()
	verifyM5baAssertError(t, func() (Result, error) {
		return Run(classfile, method, args, verifyM5caGasLimit)
	}, "BytecodeError(uint256,uint256)", code, uint64(pc))
}

// verifyM5caInstructionWidth is a boundary-aware test decoder. In particular it
// skips switch payload words and wide operands; tests never locate instructions
// by scanning arbitrary bytes which may merely resemble opcodes in table data.
func verifyM5caInstructionWidth(t *testing.T, code []byte, pc int) int {
	t.Helper()
	if pc < 0 || pc >= len(code) {
		t.Fatalf("invalid instruction pc %d", pc)
	}
	width := 1
	switch code[pc] {
	case 0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9, 0xbc:
		width = 2
	case 0x11, 0x13, 0x14, 0x84,
		0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8,
		0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xbb, 0xbd, 0xc0, 0xc1, 0xc6, 0xc7:
		width = 3
	case 0xb9, 0xba, 0xc8, 0xc9:
		width = 5
	case 0xc5:
		width = 4
	case 0xc4:
		if pc+1 >= len(code) {
			t.Fatalf("truncated wide at pc %d", pc)
		}
		if code[pc+1] == 0x84 {
			width = 6
		} else {
			width = 4
		}
	case 0xaa:
		header := pc + 1 + (4-((pc+1)%4))%4
		if header+12 > len(code) {
			t.Fatalf("truncated tableswitch at pc %d", pc)
		}
		low := int64(int32(binary.BigEndian.Uint32(code[header+4:])))
		high := int64(int32(binary.BigEndian.Uint32(code[header+8:])))
		count := high - low + 1
		if count < 0 || count > int64((len(code)-header-12)/4) {
			t.Fatalf("invalid test tableswitch count %d at pc %d", count, pc)
		}
		width = header - pc + 12 + int(count)*4
	case 0xab:
		header := pc + 1 + (4-((pc+1)%4))%4
		if header+8 > len(code) {
			t.Fatalf("truncated lookupswitch at pc %d", pc)
		}
		count := int64(int32(binary.BigEndian.Uint32(code[header+4:])))
		if count < 0 || count > int64((len(code)-header-8)/8) {
			t.Fatalf("invalid test lookupswitch count %d at pc %d", count, pc)
		}
		width = header - pc + 8 + int(count)*8
	}
	if pc+width > len(code) {
		t.Fatalf("truncated opcode 0x%02x at pc %d", code[pc], pc)
	}
	return width
}

func verifyM5caInstructionPC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc := 0; pc < len(code); pc += verifyM5caInstructionWidth(t, code, pc) {
		if code[pc] == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode 0x%02x occurrence %d absent at decoded boundaries", opcode, occurrence)
	return -1
}

func verifyM5caRequireDecodedOpcode(t *testing.T, code []byte, wantPC int, opcode byte) {
	t.Helper()
	for pc := 0; pc < len(code); pc += verifyM5caInstructionWidth(t, code, pc) {
		if pc == wantPC {
			if code[pc] != opcode {
				t.Fatalf("decoded pc %d opcode=0x%02x want 0x%02x", pc, code[pc], opcode)
			}
			return
		}
	}
	t.Fatalf("pc %d is not an instruction boundary", wantPC)
}

func verifyM5caRequireOpcode(t *testing.T, code []byte, opcode byte) {
	t.Helper()
	_ = verifyM5caInstructionPC(t, code, opcode, 0)
}
