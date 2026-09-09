// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"os"
	"testing"
)

const mcLB0ReviewRuntimeHash = "ff9c9ff093e9d4885d7546e01db7aacd95cf999d5cf9b6d6b130fd43b791b982"

// These probes deliberately do not replay the 64-row catalogue. They compile
// separate bounded Java-8-target fixtures and submit their unchanged class bytes
// through Run/RunClasses, whose production path ABI-packs them into geth's EVM.

func TestMCLB0ReviewArtifactAndCurrentRunnerBoundary(t *testing.T) {
	runtimeCode, err := Runtime()
	if err != nil {
		t.Fatal(err)
	}
	digest := sha256.Sum256(runtimeCode)
	if len(runtimeCode) != 166334 || hex.EncodeToString(digest[:]) != mcLB0ReviewRuntimeHash {
		t.Fatalf("runtime bytes/hash=%d/%x, want 166334/%s", len(runtimeCode), digest, mcLB0ReviewRuntimeHash)
	}
	currentRunner, err := os.ReadFile("jvmevm.go")
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(currentRunner, []byte("runtime.Execute(code, input, cfg)")) {
		t.Fatal("current production runner no longer executes the embedded artifact through geth EVM")
	}
	for _, forbidden := range [][]byte{[]byte("os/exec"), []byte("javaevm"), []byte("exec.Command")} {
		if bytes.Contains(currentRunner, forbidden) {
			t.Fatalf("current production runner contains forbidden host execution marker %q", forbidden)
		}
	}
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"ReviewBoundary.java": `public final class ReviewBoundary { public static int run(){return "evm".length();} }`,
	}, "ReviewBoundary")
	result := mcLB0VerifyAssertValue(t, func() (Result, error) {
		return Run(compiled.classes["ReviewBoundary"], "run", nil, mcLB0VerifyOrdinaryGas)
	}, 3)
	if result.RuntimeSHA256 != mcLB0ReviewRuntimeHash || result.GasUsed == 0 {
		t.Fatalf("executed runtime hash/gas=%q/%d", result.RuntimeSHA256, result.GasUsed)
	}
	t.Logf("actual geth EVM runtime bytes=%d SHA256=%s gas=%d", len(runtimeCode), result.RuntimeSHA256, result.GasUsed)
}

func TestMCLB0ReviewMUTF8PrecedenceNotInCatalogue(t *testing.T) {
	for _, tc := range []struct {
		name    string
		payload []byte
		code    uint64
		rel     int
	}{
		// Invalid leads win even when fewer than four bytes remain.
		{"truncated-four-byte-lead", []byte{0xf0}, 2, 0},
		{"truncated-invalid-lead", []byte{0xff}, 2, 0},
		// Continuation validity wins before the otherwise-overlong value check.
		{"overlong-two-bad-continuation", []byte{0xc0, 0x00}, 4, 1},
		{"overlong-three-bad-third", []byte{0xe0, 0x80, 0x41}, 4, 2},
		{"c1-overlong", []byte{0xc1, 0xbf}, 5, 0},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw, cpIndex, payloadOffset := mcLB0VerifyLiteralClass(t, "ReviewMUTF", tc.payload, false, true, 2, false)
			result := mcLB0VerifyAssertStringConstantError(t, func() (Result, error) {
				return Run(raw, "run", nil, mcLB0VerifyOrdinaryGas)
			}, tc.code, 0, uint64(cpIndex), uint64(payloadOffset+tc.rel))
			t.Logf("gas=%d", result.GasUsed)
		})
	}
}

func TestMCLB0ReviewNonStringInterfaceAndSpecialDispatch(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"ReviewSeq.java": `public final class ReviewSeq implements CharSequence {
			private final int n; public ReviewSeq(int n){this.n=n;}
			public int length(){return n;} public char charAt(int i){return (char)(65+i);}
			public CharSequence subSequence(int a,int b){return this;} public String toString(){return "seq";}
		}`,
		"ReviewCmp.java": `public final class ReviewCmp implements Comparable<ReviewCmp> {
			private final int n; public ReviewCmp(int n){this.n=n;} public int compareTo(ReviewCmp x){return n-x.n;}
		}`,
		"ReviewDefault.java":     `public interface ReviewDefault { default int value(){return 31;} }`,
		"ReviewDefaultImpl.java": `public final class ReviewDefaultImpl implements ReviewDefault { public int special(){return ReviewDefault.super.value();} }`,
		"ReviewDispatch.java": `public final class ReviewDispatch {
			public static int sequence(){CharSequence q=new ReviewSeq(3);return q.length()+q.charAt(1)+q.subSequence(0,1).length()+q.toString().length();}
			@SuppressWarnings({"rawtypes","unchecked"}) public static int comparable(){Comparable q=new ReviewCmp(8);int r=q.compareTo(new ReviewCmp(3));try{q.compareTo(new Object());return 0;}catch(ClassCastException e){return r+8;}}
			public static int special(){return new ReviewDefaultImpl().special();}
		}`,
		"ReviewDispatchOracle.java": `public final class ReviewDispatchOracle {public static void main(String[] x){System.out.print(ReviewDispatch.sequence()+","+ReviewDispatch.comparable()+","+ReviewDispatch.special());}}`,
	}, "ReviewSeq", "ReviewCmp", "ReviewDefault", "ReviewDefaultImpl", "ReviewDispatch", "ReviewDispatchOracle")
	mcLB0VerifySameRawJava8And21(t, compiled.dir, "ReviewDispatchOracle", "75,13,31")
	bundle := [][]byte{
		compiled.classes["ReviewSeq"], compiled.classes["ReviewCmp"],
		compiled.classes["ReviewDefault"], compiled.classes["ReviewDefaultImpl"],
		compiled.classes["ReviewDispatch"],
	}
	for _, tc := range []struct {
		method string
		want   int32
	}{{"sequence", 75}, {"comparable", 13}, {"special", 31}} {
		t.Run(tc.method, func(t *testing.T) {
			result := mcLB0VerifyAssertValue(t, func() (Result, error) {
				return RunClasses(bundle, "ReviewDispatch", tc.method, nil, mcLB0ReviewOrdinaryGas)
			}, tc.want)
			t.Logf("gas=%d", result.GasUsed)
		})
	}
	// The user CharSequence.subSequence and Comparable bridge above execute their
	// ordinary Code. They do not inherit String's deferred intrinsic or native
	// compareTo binding merely because they implement represented interfaces.
}

func TestMCLB0ReviewFreshInitializedAndPoisonedStringReferences(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"ReviewFresh.java": `public final class ReviewFresh {
			static final String A="alias",B="alias"; static String C; static {C=A;}
			static String id(String x){return x;}
			public static int run(){String x="alias";Object[] a={A,C,x};return (A==B?10000:0)+(C==A?1000:0)+(id(x)==A?100:0)+(a[0]==a[1]?10:0)+(a[2] instanceof String?1:0);}
		}`,
		"ReviewPoison.java": `public final class ReviewPoison {
			static final String P="poison"; static {if(P.length()==6)fail();}
			static void fail(){int z=0;z=1/z;} public static int read(){return P.length();}
		}`,
		"ReviewLifecycle.java": `public final class ReviewLifecycle {
			public static int poison(){int r=0;try{ReviewPoison.read();}catch(ExceptionInInitializerError e){r=3;}try{ReviewPoison.read();}catch(NoClassDefFoundError e){r+=12;}return r;}
		}`,
		"ReviewLifecycleOracle.java": `public final class ReviewLifecycleOracle {public static void main(String[] x){System.out.print(ReviewFresh.run()+","+ReviewLifecycle.poison());}}`,
	}, "ReviewFresh", "ReviewPoison", "ReviewLifecycle", "ReviewLifecycleOracle")
	mcLB0VerifySameRawJava8And21(t, compiled.dir, "ReviewLifecycleOracle", "11111,15")
	fresh := mcLB0VerifyAssertValue(t, func() (Result, error) {
		return Run(compiled.classes["ReviewFresh"], "run", nil, mcLB0ReviewOrdinaryGas)
	}, 11111)
	poison := mcLB0VerifyAssertValue(t, func() (Result, error) {
		return RunClasses([][]byte{compiled.classes["ReviewPoison"], compiled.classes["ReviewLifecycle"]}, "ReviewLifecycle", "poison", nil, mcLB0ReviewOrdinaryGas)
	}, 15)
	t.Logf("fresh gas=%d poison gas=%d", fresh.GasUsed, poison.GasUsed)
}

func TestMCLB0ReviewUnsupportedAndSpecialStringCallBoundaries(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"ReviewUnsupported.java": `public final class ReviewUnsupported {
			public static int staticAPI(int x){return String.valueOf(x).length();}
			public static int nativeCall(){return "x".length();}
		}`,
	}, "ReviewUnsupported")
	raw := compiled.classes["ReviewUnsupported"]
	staticMethod := mcLB0VerifyParse(t, raw).method(t, "staticAPI", "(I)I")
	staticPC := mcLB0VerifyOpcodePC(t, staticMethod.code, 0xb8, 0)
	staticResult := mcLB0VerifyAssertError(t, func() (Result, error) {
		return Run(raw, "staticAPI", []int32{7}, mcLB0ReviewOrdinaryGas)
	}, "StringProfileError(uint256,uint256)", 1, uint64(staticPC))

	// A malformed classfile cannot reach a String intrinsic through invokespecial.
	// Change only the invokevirtual opcode; leave the String Methodref untouched.
	special := append([]byte(nil), raw...)
	p := mcLB0VerifyParse(t, special)
	m := p.method(t, "nativeCall", "()I")
	pc := mcLB0VerifyFindInvoke(t, special, "nativeCall", "length", "()I")
	if m.code[pc] != 0xb6 {
		t.Fatalf("nativeCall opcode at %d = 0x%02x", pc, m.code[pc])
	}
	special[m.codeOffset+pc] = 0xb7
	specialResult := mcLB0VerifyAssertError(t, func() (Result, error) {
		return Run(special, "nativeCall", nil, mcLB0ReviewOrdinaryGas)
	}, "ObjectError(uint256,uint256)", 3, uint64(pc))
	t.Logf("unsupported static gas=%d malformed special gas=%d", staticResult.GasUsed, specialResult.GasUsed)
}

func TestMCLB0ReviewMalformedStringDescriptorMustUseExistingCallError(t *testing.T) {
	compiled := mcLB0VerifyCompile(t, map[string]string{
		"ReviewOrdinaryMalformed.java": `public final class ReviewOrdinaryMalformed {public int target(int x){return x;}public static int run(){return new ReviewOrdinaryMalformed().target(1);}}`,
		"ReviewMalformed.java": `public final class ReviewMalformed {
			public static int run(){return "x".isEmpty()?1:0;}
			public static int iface(int ignored){CharSequence q="x";return q.length();}
			public static int staticAPI(int x){return String.valueOf(x).length();}
		}`,
	}, "ReviewOrdinaryMalformed", "ReviewMalformed")

	ordinary, ordinaryPC := mcLB0ReviewMutateCallDescriptor(t,
		compiled.classes["ReviewOrdinaryMalformed"], "run", "target", "(I)I", 3, 'Q')
	// This establishes the pre-LB0 malformed-callee rule on the same invokevirtual
	// path: a resolved ordinary declaration with a malformed descriptor is CallError4.
	ordinaryResult := mcLB0VerifyAssertError(t, func() (Result, error) {
		return Run(ordinary, "run", nil, mcLB0ReviewOrdinaryGas)
	}, "CallError(uint256,uint256)", 4, uint64(ordinaryPC))
	t.Logf("ordinary malformed-descriptor baseline gas=%d", ordinaryResult.GasUsed)

	for _, tc := range []struct {
		name, method, member, descriptor string
		descriptorByte                   int
		args                             []int32
	}{
		{"virtual-String", "run", "isEmpty", "()Z", 2, nil},
		{"interface-CharSequence", "iface", "length", "()I", 2, []int32{0}},
		{"static-String", "staticAPI", "valueOf", "(I)Ljava/lang/String;", 1, []int32{7}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			raw, pc := mcLB0ReviewMutateCallDescriptor(t,
				compiled.classes["ReviewMalformed"], tc.method, tc.member, tc.descriptor, tc.descriptorByte, 'Q')
			// Frozen LB0 requires malformed descriptors to fail under existing call-shape
			// rules before the String unsupported-profile boundary. At f50fe14 all
			// three shapes instead return StringProfileError(1,pc).
			mcLB0VerifyAssertError(t, func() (Result, error) {
				return Run(raw, tc.method, tc.args, mcLB0ReviewOrdinaryGas)
			}, "CallError(uint256,uint256)", 4, uint64(pc))
		})
	}
}

func mcLB0ReviewMutateCallDescriptor(t *testing.T, original []byte, method, member, descriptor string, byteAt int, replacement byte) ([]byte, int) {
	t.Helper()
	raw := append([]byte(nil), original...)
	parsed := mcLB0VerifyParse(t, raw)
	pc := mcLB0ReviewFindCall(t, parsed, method, member, descriptor)
	var selected mcLB0VerifyMethod
	for _, candidate := range parsed.methods {
		if candidate.name == method {
			selected = candidate
			break
		}
	}
	if selected.code == nil {
		t.Fatalf("method %s absent", method)
	}
	ref := binary.BigEndian.Uint16(selected.code[pc+1:])
	nameAndType := binary.BigEndian.Uint16(raw[parsed.cp[ref].offset+3:])
	descriptorIndex := binary.BigEndian.Uint16(raw[parsed.cp[nameAndType].offset+3:])
	entry := parsed.cp[descriptorIndex]
	if parsed.utf8[descriptorIndex] != descriptor || byteAt < 0 || byteAt >= entry.payloadLength {
		t.Fatalf("descriptor mutation target=%q byte=%d", parsed.utf8[descriptorIndex], byteAt)
	}
	raw[entry.payloadOffset+byteAt] = replacement
	return raw, pc
}

func mcLB0ReviewFindCall(t *testing.T, parsed mcLB0VerifyClass, method, member, descriptor string) int {
	t.Helper()
	var selected mcLB0VerifyMethod
	for _, candidate := range parsed.methods {
		if candidate.name == method {
			selected = candidate
			break
		}
	}
	if selected.code == nil {
		t.Fatalf("method %s absent", method)
	}
	for pc := 0; pc < len(selected.code); pc += mcLB0VerifyInstructionWidth(t, selected.code, pc) {
		op := selected.code[pc]
		if op != 0xb6 && op != 0xb8 && op != 0xb9 {
			continue
		}
		ref := binary.BigEndian.Uint16(selected.code[pc+1:])
		if ref == 0 || int(ref) >= len(parsed.cp) || (parsed.cp[ref].tag != 10 && parsed.cp[ref].tag != 11) {
			continue
		}
		nameAndType := binary.BigEndian.Uint16(parsed.data[parsed.cp[ref].offset+3:])
		if nameAndType == 0 || int(nameAndType) >= len(parsed.cp) || parsed.cp[nameAndType].tag != 12 {
			continue
		}
		name := binary.BigEndian.Uint16(parsed.data[parsed.cp[nameAndType].offset+1:])
		desc := binary.BigEndian.Uint16(parsed.data[parsed.cp[nameAndType].offset+3:])
		if parsed.utf8[name] == member && parsed.utf8[desc] == descriptor {
			return pc
		}
	}
	t.Fatalf("call %s%s absent in %s", member, descriptor, method)
	return 0
}

// Keep the review cap independently named even though it intentionally equals the
// frozen local ordinary profile; no historical budget is modified.
const mcLB0ReviewOrdinaryGas = uint64(100_000_000)
