// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const (
	verifyM4dGasLimit         = uint64(100_000_000)
	verifyM4dCapacityGasLimit = uint64(250_000_000)
	verifyM4dAaload           = byte(0x32)
	verifyM4dAastore          = byte(0x53)
	verifyM4dAnewarray        = byte(0xbd)
)

// All Java in this file is trusted, locally generated test input. Mutations are
// confined to copies of javac --release 8 classfiles and isolate bytecode/CP
// shapes javac cannot emit. There is no production parser or heap test hook.

func TestVerifyM4dReferenceArrayDefaultsIdentityFieldsCallsAndReturns(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"refbasic/Base.java": `package refbasic; public class Base {
            public int value; public Base(int value){this.value=value;}
        }`,
		"refbasic/Child.java": `package refbasic; public final class Child extends Base {
            public Child(int value){super(value);}
        }`,
		"refbasic/Holder.java": `package refbasic; public final class Holder {
            public Base[] instance; public static Base[] shared;
            public final Base[] fixed=new Base[1];
            static Base[] pass(Base[] value){return value;}
            static void store(Base[] value,Base item){value[0]=item;}
        }`,
		"refbasic/Root.java": `package refbasic; public final class Root {
            public static int defaults(){Base[] a=new Base[2],b=new Base[0],alias=a;
                return (a[0]==null?100:0)+(a[1]==null?10:0)+(a==alias?2:0)+(a!=b?1:0)+b.length;}
            public static int transport(){Child[] actual=new Child[2];Base[] wide=Holder.pass(actual);
                Holder h=new Holder();h.instance=wide;Holder.shared=wide;h.fixed[0]=new Base(4);
                Holder.store(wide,new Child(7));Base[] returned=Holder.pass(wide);
                return returned[0].value*1000+(h.instance==actual?100:0)
                    +(Holder.shared==actual?10:0)+h.fixed[0].value;}
        }`,
	}, "refbasic/Base", "refbasic/Child", "refbasic/Holder", "refbasic/Root")
	verifyM4dAssertNoOpcode(t, classes, 0xc5) // multianewarray stays out of M4d.
	bundle := verifyM4dBundle(classes)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "refbasic/Root", "defaults", nil, verifyM4dGasLimit)
	}, 113)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "refbasic/Root", "transport", nil, verifyM4dGasLimit)
	}, 7114)
	// Statics and all array/object identities are invocation-local.
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "refbasic/Root", "transport", nil, verifyM4dGasLimit)
	}, 7114)
}

func TestVerifyM4dRootReferenceArraySignaturesRemainRejected(t *testing.T) {
	classfile := compileJava(t, "ReferenceArrayRoots", `public final class ReferenceArrayRoots {
        public static int takes(ReferenceArrayRoots[] value){return value==null?1:2;}
        public static int nested(ReferenceArrayRoots[][] value){return value==null?1:2;}
        public static ReferenceArrayRoots[] gives(){return new ReferenceArrayRoots[1];}
        public static int scalar(int value){return value;}
    }`)
	for _, tc := range []struct {
		method string
		args   []int32
	}{{"takes", nil}, {"takes", []int32{0}}, {"nested", nil}, {"gives", nil}} {
		t.Run(tc.method+fmt.Sprint(tc.args), func(t *testing.T) {
			result, err := Run(classfile, tc.method, tc.args, verifyM4dGasLimit)
			verifyM4dAssertMethodError(t, result, err, 11)
		})
	}
	verifyM4dAssertValue(t, func() (Result, error) {
		return Run(classfile, "scalar", []int32{9}, verifyM4dGasLimit)
	}, 9)
}

func TestVerifyM4dRecursiveCovarianceNestedConstructionCastsAndTypeTests(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"covar/Base.java":  `package covar; public class Base { public int value; public Base(int x){value=x;} }`,
		"covar/Child.java": `package covar; public final class Child extends Base { public Child(int x){super(x);} }`,
		"covar/Root.java": `package covar; public final class Root {
            static int sum(Base[][] a,int row,int col){if(row==a.length)return 0;
                if(col==a[row].length)return sum(a,row+1,0);
                return a[row][col].value+sum(a,row,col+1);}
            public static int nested(){Child[][] child=new Child[1][];child[0]=new Child[2];
                child[0][0]=new Child(3);child[0][1]=new Child(4);Base[][] base=child;
                Object[] outer=child;Object[][] objects=child;
                return sum(base,0,0)*100+(outer==child?10:0)+(objects==child?1:0);}
            public static int matrix(){Child[] c1=new Child[1];Child[][] c2=new Child[1][];
                int[] i1=new int[1];int[][] i2=new int[1][];
                return (c1 instanceof Base[]?1:0)+(c1 instanceof Object[]?2:0)
                    +(c2 instanceof Base[][]?4:0)+(c2 instanceof Object[][]?8:0)
                    +(i1 instanceof Object?16:0)+(!((Object)i1 instanceof Object[])?32:0)
                    +(i2 instanceof Object[]?64:0)+(!((Object)i2 instanceof Object[][])?128:0)
                    +(((Base[])c1)==c1?256:0)+(((Object[])i2)==i2?512:0);}
            public static int heterogeneous(){Object[] values=new Object[3];Child child=new Child(6);
                int[] ints=new int[1];Child[] children=new Child[0];ints[0]=7;
                values[0]=child;values[1]=ints;values[2]=children;
                return (((Child)values[0])==child?100:0)+(((int[])values[1])==ints?10:0)
                    +(((Child[])values[2])==children?1:0)+((int[])values[1])[0];}
        }`,
	}, "covar/Base", "covar/Child", "covar/Root")
	verifyM4dAssertNoOpcode(t, classes, 0xc5) // nested rows are assembled explicitly.
	bundle := verifyM4dBundle(classes)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "covar/Root", "nested", nil, verifyM4dGasLimit)
	}, 711)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "covar/Root", "matrix", nil, verifyM4dGasLimit)
	}, 1023)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "covar/Root", "heterogeneous", nil, verifyM4dGasLimit)
	}, 118)
}

func TestVerifyM4dAastoreUsesActualComponentAndJavaCheckOrder(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"store/Base.java":  `package store; public class Base { public Base(){} }`,
		"store/Child.java": `package store; public final class Child extends Base { public Child(){} }`,
		"store/Root.java": `package store; public final class Root {
            public static int compatibleNull(){Base[] value=new Child[1];value[0]=null;return value[0]==null?1:0;}
            public static int incompatible(){Object[] value=new Child[1];value[0]=new Base();return 1;}
            public static int outOfBounds(){Object[] value=new Child[1];value[1]=new Base();return 1;}
            public static int negative(){Object[] value=new Child[1];value[-1]=new Base();return 1;}
            public static int nullReceiver(){Object[] value=null;value[99]=new Base();return 1;}
        }`,
	}, "store/Base", "store/Child", "store/Root")
	bundle := verifyM4dBundle(classes)
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "store/Root", "compatibleNull", nil, verifyM4dGasLimit)
	}, 1)
	verifyM4dAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "store/Root", "incompatible", nil, verifyM4dGasLimit)
	}, "java.lang.ArrayStoreException", 9)
	for _, method := range []string{"outOfBounds", "negative"} {
		t.Run(method, func(t *testing.T) {
			verifyM4dAssertException(t, func() (Result, error) {
				return RunClasses(bundle, "store/Root", method, nil, verifyM4dGasLimit)
			}, "java.lang.ArrayIndexOutOfBoundsException", 5)
		})
	}
	verifyM4dAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "store/Root", "nullReceiver", nil, verifyM4dGasLimit)
	}, "java.lang.NullPointerException", 6)
}

func TestVerifyM4dMissingComponentResolvesBeforeEveryLengthCheck(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"missingref/Component.java": `package missingref; public class Component { }`,
		"missingref/Root.java": `package missingref; public final class Root {
            public static int run(int n){return new Component[n].length;}
        }`,
	}, "missingref/Component", "missingref/Root")
	root := classes["missingref/Root"]
	verifyM4dAssertDeclaredClass(t, root, "missingref/Root")
	pc, component := verifyM4dAnewarraySite(t, root, "run")
	if component != "missingref/Component" {
		t.Fatalf("anewarray component=%q, want genuinely omitted missingref/Component", component)
	}
	// Deliberately supply only Root. Component is neither declared in Root nor an
	// accidental inner class/bundle entry.
	for _, n := range []int32{-1, 0, 1} {
		t.Run(fmt.Sprint(n), func(t *testing.T) {
			verifyM4dAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{root}, "missingref/Root", "run", []int32{n}, verifyM4dGasLimit)
			}, "LinkError(uint256,uint256)", 4, uint64(pc))
		})
	}
}

func TestVerifyM4dComponentAllocationDoesNotInitializeOrConstructAndAllowsAbstract(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"component/Lazy.java": `package component; public class Lazy {
            static int starts=1/zero();static int zero(){return 0;}
            public Lazy(){int impossible=1/zero();}
        }`,
		"component/AbstractValue.java": `package component; public abstract class AbstractValue { }`,
		"component/Root.java": `package component; public final class Root {
            public static int lazy(int n){Lazy[] value=new Lazy[n];if(n!=0)value[0]=null;
                return value.length+(n==0?0:(value[0]==null?10:0));}
            public static int abstractArray(){AbstractValue[] value=new AbstractValue[1];return value[0]==null?1:0;}
        }`,
	}, "component/Lazy", "component/AbstractValue", "component/Root")
	bundle := verifyM4dBundle(classes)
	for _, tc := range []struct{ n, want int32 }{{0, 0}, {1, 11}} {
		verifyM4dAssertValue(t, func() (Result, error) {
			return RunClasses(bundle, "component/Root", "lazy", []int32{tc.n}, verifyM4dGasLimit)
		}, tc.want)
	}
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(bundle, "component/Root", "abstractArray", nil, verifyM4dGasLimit)
	}, 1)
}

func TestVerifyM4dRank255BoundaryWithoutUnsafeHostAllocation(t *testing.T) {
	original := compileJava(t, "RankShape", `public final class RankShape {
        public static int run(){Object[] value=new Object[0];return value.length;}
    }`)
	for _, tc := range []struct {
		name          string
		componentRank int
		wantOverflow  bool
	}{
		{"rank254-to-255", 254, false},
		{"rank255-to-256", 255, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			component := strings.Repeat("[", tc.componentRank) + "I"
			classfile := verifyM4dRetargetAnewarrayToAppendedName(t, original, "run", component)
			pc, got := verifyM4dAnewarraySite(t, classfile, "run")
			if got != component {
				t.Fatalf("component=%q, want rank %d descriptor", got, tc.componentRank)
			}
			if tc.wantOverflow {
				verifyM4dAssertError(t, func() (Result, error) {
					return Run(classfile, "run", nil, verifyM4dGasLimit)
				}, "ArrayError(uint256,uint256)", 2, uint64(pc))
			} else {
				// EVM-only zero-length allocation exercises metadata rank 255; no
				// rank-sized or huge host-JVM allocation is attempted.
				verifyM4dAssertValue(t, func() (Result, error) {
					return Run(classfile, "run", nil, verifyM4dGasLimit)
				}, 0)
			}
		})
	}
}

func TestVerifyM4dAnewarrayMalformedCPNamesTargetsTruncationAndBranch(t *testing.T) {
	original := compileJava(t, "RefShape", `public final class RefShape {
        public static int run(){RefShape[] value=new RefShape[1];return value.length;}
        public static int padding(){int x=0;x=x+1;x=x+2;x=x+3;x=x+4;return x;}
    }`)
	pc, _ := verifyM4dAnewarraySite(t, original, "run")
	for _, tc := range []struct {
		name string
		make func() []byte
	}{
		{"operand-zero", func() []byte {
			return verifyM4dMutate(t, original, func(_ []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], 0)
			})
		}},
		{"operand-range", func() []byte {
			return verifyM4dMutate(t, original, func(_ []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], uint16(c.cpCount))
			})
		}},
		{"wrong-tag", func() []byte {
			out, alias := verifyM4dAppendClassForExistingName(t, original, "RefShape")
			return verifyM4dMutate(t, out, func(raw []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], alias)
				raw[c.entry(t, alias).offset] = 8
			})
		}},
		{"zero-name", func() []byte {
			out, alias := verifyM4dAppendClassForExistingName(t, original, "RefShape")
			return verifyM4dMutate(t, out, func(raw []byte, c staticsClass) {
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], alias)
				binary.BigEndian.PutUint16(raw[c.entry(t, alias).offset+1:], 0)
			})
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			verifyM4dAssertError(t, func() (Result, error) {
				return Run(tc.make(), "run", nil, verifyM4dGasLimit)
			}, "TypeError(uint256,uint256)", 1, uint64(pc))
		})
	}
	for _, name := range []string{"[Qbad", "bad.Name", strings.Repeat("[", 256) + "I"} {
		t.Run("name-"+fmt.Sprint(len(name)), func(t *testing.T) {
			bad := verifyM4dRetargetAnewarrayToAppendedName(t, original, "run", name)
			verifyM4dAssertError(t, func() (Result, error) {
				return Run(bad, "run", nil, verifyM4dGasLimit)
			}, "TypeError(uint256,uint256)", 1, uint64(pc))
		})
	}

	truncated := verifyM4dRewriteAtEnd(t, original, "padding", "()I", verifyM4dAnewarray)
	truncatedPC := len(parseStaticsClass(t, truncated).method(t, "padding", "()I").code) - 1
	verifyM4dAssertError(t, func() (Result, error) {
		return Run(truncated, "padding", nil, verifyM4dGasLimit)
	}, "BytecodeError(uint256,uint256)", 2, uint64(truncatedPC))

	classIndex := verifyM4dClassIndex(t, parseStaticsClass(t, original), "RefShape")
	branchCode := []byte{0x03, 0x99, 0, 5, 0x04, verifyM4dAnewarray, byte(classIndex >> 8), byte(classIndex), 0x57, 0x03, 0xac}
	branch := verifyM4dRewriteCode(t, original, "padding", "()I", branchCode)
	verifyM4dAssertError(t, func() (Result, error) {
		return Run(branch, "padding", nil, verifyM4dGasLimit)
	}, "BytecodeError(uint256,uint256)", 12, 1)
}

func TestVerifyM4dDeferredInterfacePrimitiveAndInaccessibleComponents(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"deferref/I.java":      `package deferref; public interface I { }`,
		"deferref/Target.java": `package deferref; public class Target { }`,
		"deferuser/Root.java": `package deferuser; public final class Root {
            public static int iface(){return new deferref.I[0].length;}
            public static int primitive(){return new long[0][].length;}
            public static int target(){return new deferref.Target[0].length;}
        }`,
	}, "deferref/I", "deferref/Target", "deferuser/Root")
	root := classes["deferuser/Root"]
	// Interface components are supported from M4f-a; primitive long[] is not.
	verifyM4dAssertValue(t, func() (Result, error) {
		return RunClasses(verifyM4dBundle(classes), "deferuser/Root", "iface", nil, verifyM4dGasLimit)
	}, 0)
	for _, method := range []string{"primitive"} {
		pc, _ := verifyM4dAnewarraySite(t, root, method)
		verifyM4dAssertError(t, func() (Result, error) {
			return RunClasses(verifyM4dBundle(classes), "deferuser/Root", method, nil, verifyM4dGasLimit)
		}, "TypeError(uint256,uint256)", 2, uint64(pc))
	}
	inaccessible := verifyM4dMutate(t, classes["deferref/Target"], func(raw []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(raw[c.cpEnd:])
		binary.BigEndian.PutUint16(raw[c.cpEnd:], flags&^accPublic)
	})
	pc, _ := verifyM4dAnewarraySite(t, root, "target")
	verifyM4dAssertError(t, func() (Result, error) {
		return RunClasses([][]byte{classes["deferref/I"], inaccessible, root}, "deferuser/Root", "target", nil, verifyM4dGasLimit)
	}, "TypeError(uint256,uint256)", 2, uint64(pc))
}

func TestVerifyM4dTypedStackUninitializedAndWrongHeapOpcodes(t *testing.T) {
	original := compileJava(t, "RefKinds", `public final class RefKinds {
        public RefKinds(){}
        public static int refLoad(){RefKinds[] a=new RefKinds[1];return a[0]==null?1:0;}
        public static int refStore(){RefKinds[] a=new RefKinds[1];a[0]=null;return 1;}
        public static int intLoad(){int[] a=new int[1];return a[0];}
        public static int intStore(){int[] a=new int[1];a[0]=2;return 1;}
        public static int padding(){int x=0;x=x+1;x=x+2;x=x+3;x=x+4;x=x+5;return x;}
    }`)
	for _, tc := range []struct {
		method                   string
		from, to                 byte
		producerFrom, producerTo byte
	}{
		{"refLoad", verifyM4dAaload, 0x2e, 0, 0},
		{"refStore", verifyM4dAastore, 0x4f, 0x01, 0x03},
		{"intLoad", 0x2e, verifyM4dAaload, 0, 0},
		{"intStore", 0x4f, verifyM4dAastore, 0x05, 0x01},
	} {
		t.Run(tc.method, func(t *testing.T) {
			bad, opPC := verifyM4dReplaceOpcode(t, original, tc.method, tc.from, tc.to)
			if tc.producerFrom != 0 {
				bad = verifyM4dMutate(t, bad, func(_ []byte, c staticsClass) {
					code := c.namedMethod(t, tc.method).code
					if opPC == 0 {
						t.Fatalf("%s store at pc 0 has no value producer", tc.method)
					}
					if code[opPC-1] != tc.producerFrom {
						t.Fatalf("%s value producer at pc %d is 0x%02x, want 0x%02x", tc.method, opPC-1, code[opPC-1], tc.producerFrom)
					}
					code[opPC-1] = tc.producerTo
				})
			}
			verifyM4dAssertError(t, func() (Result, error) {
				return Run(bad, tc.method, nil, verifyM4dGasLimit)
			}, "ReferenceError(uint256,uint256)", 1, uint64(opPC))
		})
	}

	classIndex := verifyM4dClassIndex(t, parseStaticsClass(t, original), "RefKinds")
	cases := []struct {
		name        string
		code        []byte
		faultOpcode byte
	}{
		{"int-as-reference", []byte{0x04, verifyM4dAnewarray, byte(classIndex >> 8), byte(classIndex), 0x03, 0x04, verifyM4dAastore, 0x04, 0xac}, verifyM4dAastore},
		{"reference-as-int", []byte{0x04, verifyM4dAnewarray, byte(classIndex >> 8), byte(classIndex), 0x03, 0x01, 0x4f, 0x04, 0xac}, 0x4f},
		{"uninitialized-element", []byte{0x04, verifyM4dAnewarray, byte(classIndex >> 8), byte(classIndex), 0x03, verifyM4bNew, byte(classIndex >> 8), byte(classIndex), verifyM4dAastore, 0x04, 0xac}, verifyM4dAastore},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			bad := verifyM4dRewriteCode(t, original, "padding", "()I", tc.code)
			gotCode := parseStaticsClass(t, bad).method(t, "padding", "()I").code
			if !bytes.Equal(gotCode[:len(tc.code)], tc.code) {
				t.Fatalf("handcrafted stack program changed: got %x want prefix %x", gotCode, tc.code)
			}
			faultPC := verifyM4dOpcodePC(t, tc.code, tc.faultOpcode, 0)
			if gotCode[faultPC] != tc.faultOpcode {
				t.Fatalf("fault opcode at derived pc %d is 0x%02x, want 0x%02x", faultPC, gotCode[faultPC], tc.faultOpcode)
			}
			verifyM4dAssertError(t, func() (Result, error) {
				return Run(bad, "padding", nil, verifyM4dGasLimit)
			}, "BytecodeError(uint256,uint256)", 14, uint64(faultPC))
		})
	}
}

func TestVerifyM4dDescriptorArrayMismatchIsReference2NotWrongHeap1(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"descref/A.java": `package descref; public class A { }`,
		"descref/B.java": `package descref; public class B { }`,
		"descref/Root.java": `package descref; public final class Root {
            A[] field;static A[] shared;
            static int accept(A[] value){return value.length;}
            static A[] give(){return new A[1];}
            public static int argument(){return accept(new A[1]);}
            public static int instanceField(){Root r=new Root();r.field=new A[1];return r.field.length;}
            public static int staticField(){shared=new A[1];return shared.length;}
            public static int returned(){return give().length;}
            static int anchor(){return new B[0].length;}
        }`,
	}, "descref/A", "descref/B", "descref/Root")
	root := classes["descref/Root"]
	bIndex := verifyM4dClassIndex(t, parseStaticsClass(t, root), "descref/B")
	for _, tc := range []struct {
		method   string
		boundary byte
	}{
		{"argument", 0xb8},
		{"instanceField", 0xb5},
		{"staticField", 0xb3},
		{"give", 0xb0},
	} {
		t.Run(tc.method, func(t *testing.T) {
			bad := verifyM4dMutate(t, root, func(_ []byte, c staticsClass) {
				m := c.namedMethod(t, tc.method)
				arrayPC := verifyM4dOpcodePC(t, m.code, verifyM4dAnewarray, 0)
				binary.BigEndian.PutUint16(m.code[arrayPC+1:], bIndex)
			})
			boundaryPC := verifyM4dOpcodePC(t, parseStaticsClass(t, bad).namedMethod(t, tc.method).code, tc.boundary, 0)
			entry := tc.method
			if tc.method == "give" {
				entry = "returned"
			}
			verifyM4dAssertError(t, func() (Result, error) {
				return RunClasses([][]byte{classes["descref/A"], classes["descref/B"], bad}, "descref/Root", entry, nil, verifyM4dGasLimit)
			}, "ReferenceError(uint256,uint256)", 2, uint64(boundaryPC))
		})
	}
}

func TestVerifyM4dSharedArrayCapsNoGCResetAndIndependentObjects(t *testing.T) {
	classfile := compileJava(t, "ReferenceCaps", `public final class ReferenceCaps {
        ReferenceCaps(){super();}
        public static int mixed(int count){Object last=null;for(int i=0;i<count;i++)
            last=(i&1)==0?(Object)new int[0]:(Object)new ReferenceCaps[0];
            return count+(last==null?0:0);}
        public static int exactElements(){Object last;
            last=new int[65536];last=new ReferenceCaps[65536];
            last=new int[65536];last=new ReferenceCaps[65536];
            return 262144+(last==null?0:0);}
        public static int overElements(){Object last;
            last=new int[65536];last=new ReferenceCaps[65536];
            last=new int[65536];last=new ReferenceCaps[65536];last=new ReferenceCaps[1];
            return last==null?0:1;}
        public static int arraysThenObjects(){Object a=null,o=null;
            for(int i=0;i<1024;i++)a=(i&1)==0?(Object)new int[0]:(Object)new ReferenceCaps[0];
            for(int i=0;i<1024;i++)o=new ReferenceCaps();
            return (a==null?0:1)+(o==null?0:1);}
    }`)
	verifyM4dAssertValue(t, func() (Result, error) {
		return Run(classfile, "mixed", []int32{1024}, verifyM4dCapacityGasLimit)
	}, 1024)
	verifyM4dAssertException(t, func() (Result, error) {
		return Run(classfile, "mixed", []int32{1025}, verifyM4dCapacityGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	verifyM4dAssertValue(t, func() (Result, error) {
		return Run(classfile, "exactElements", nil, verifyM4dCapacityGasLimit)
	}, 262144)
	verifyM4dAssertException(t, func() (Result, error) {
		return Run(classfile, "overElements", nil, verifyM4dCapacityGasLimit)
	}, "java.lang.OutOfMemoryError", 7)
	verifyM4dAssertValue(t, func() (Result, error) {
		return Run(classfile, "arraysThenObjects", nil, verifyM4dCapacityGasLimit)
	}, 2)
	// Unreachable arrays counted above (no GC), but a new invocation resets all caps.
	verifyM4dAssertValue(t, func() (Result, error) {
		return Run(classfile, "mixed", []int32{1024}, verifyM4dCapacityGasLimit)
	}, 1024)
}

func TestVerifyM4dBothArrayKindsDeferVirtualOnlyAfterResolution(t *testing.T) {
	original := compileJava(t, "ArrayVirtualM4d", `public class ArrayVirtualM4d {
        public ArrayVirtualM4d(){} public int f(){return 7;}
        public static int intArray(){return new ArrayVirtualM4d().f();}
        public static int refArray(){return new ArrayVirtualM4d().f();}
        public static int missingInt(){Object value=new int[1];return value.hashCode();}
        public static int missingRef(){Object value=new ArrayVirtualM4d[1];return value.hashCode();}
    }`)
	parsed := parseStaticsClass(t, original)
	classIndex := verifyM4dClassIndex(t, parsed, "ArrayVirtualM4d")
	for _, tc := range []struct {
		method string
		alloc  []byte
	}{
		{"intArray", []byte{0x04, 0xbc, 10}},
		{"refArray", []byte{0x04, verifyM4dAnewarray, byte(classIndex >> 8), byte(classIndex)}},
	} {
		m := parsed.method(t, tc.method, "()I")
		callRef, _ := verifyM4dMemberInstruction(t, parsed, m, 0xb6, "f", "()I")
		code := append(append([]byte(nil), tc.alloc...), 0xb6, byte(callRef>>8), byte(callRef), 0xac)
		bad := verifyM4dRewriteCode(t, original, tc.method, "()I", code)
		callPC := len(tc.alloc)
		verifyM4dAssertError(t, func() (Result, error) {
			return Run(bad, tc.method, nil, verifyM4dGasLimit)
		}, "CallError(uint256,uint256)", 4, uint64(callPC))
	}
	for _, method := range []string{"missingInt", "missingRef"} {
		pc := verifyM4dOpcodePC(t, parsed.method(t, method, "()I").code, 0xb6, 0)
		verifyM4dAssertError(t, func() (Result, error) {
			return Run(original, method, nil, verifyM4dGasLimit)
		}, "CallError(uint256,uint256)", 3, uint64(pc))
	}
}

func TestVerifyM4dASECCEEIIEAndOOGRemainExact(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"outcome/A.java": `package outcome; public class A { public A(){} }`,
		"outcome/B.java": `package outcome; public final class B { public B(){} }`,
		"outcome/Root.java": `package outcome; public final class Root {
            public static int ase(){Object[] value=new B[1];value[0]=new A();return 1;}
            public static int cce(){Object value=new B[1];return ((A[])value).length;}
        }`,
		"outcome/Init.java": `package outcome; public final class Init {
            static Object[] value=new B[1];static int result=fail();
            static int fail(){value[0]=new A();return 1;}public static int run(){return result;}
        }`,
	}, "outcome/A", "outcome/B", "outcome/Root", "outcome/Init")
	bundle := verifyM4dBundle(classes)
	verifyM4dAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "outcome/Root", "ase", nil, verifyM4dGasLimit)
	}, "java.lang.ArrayStoreException", 9)
	verifyM4dAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "outcome/Root", "cce", nil, verifyM4dGasLimit)
	}, "java.lang.ClassCastException", 8)
	verifyM4dAssertException(t, func() (Result, error) {
		return RunClasses(bundle, "outcome/Init", "run", nil, verifyM4dGasLimit)
	}, "java.lang.ExceptionInInitializerError", 3)
	result, err := RunClasses(bundle, "outcome/Root", "ase", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) || result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want unlabeled EVM out of gas", result, err)
	}
}

func TestVerifyM4dJavaExceptionDecoderKindsOneThroughNineCanonical(t *testing.T) {
	want := []string{
		"java.lang.ArithmeticException",
		"java.lang.StackOverflowError",
		"java.lang.ExceptionInInitializerError",
		"java.lang.NegativeArraySizeException",
		"java.lang.ArrayIndexOutOfBoundsException",
		"java.lang.NullPointerException",
		"java.lang.OutOfMemoryError",
		"java.lang.ClassCastException",
		"java.lang.ArrayStoreException",
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	payload := append(append([]byte(nil), selector...), make([]byte, 32)...)
	for i, class := range want {
		payload[35] = byte(i + 1)
		if got, ok := decodeJavaException(payload); !ok || got != class {
			t.Fatalf("decode kind %d=(%q,%v), want %q", i+1, got, ok, class)
		}
	}
	payload[35] = 9
	for _, bad := range [][]byte{
		append([]byte(nil), payload[:35]...),
		append(append([]byte(nil), payload...), 0),
		func() []byte { out := append([]byte(nil), payload...); out[4] = 1; return out }(),
		func() []byte { out := append([]byte(nil), payload...); out[35] = 255; return out }(),
		func() []byte { out := append([]byte(nil), payload...); out[0] ^= 1; return out }(),
	} {
		if got, ok := decodeJavaException(bad); ok || got != "" {
			t.Fatalf("noncanonical/unknown payload %x decoded as (%q,%v)", bad, got, ok)
		}
	}
}

func verifyM4dBundle(classes map[string][]byte) [][]byte {
	names := make([]string, 0, len(classes))
	for name := range classes {
		names = append(names, name)
	}
	for i := range names {
		for j := i + 1; j < len(names); j++ {
			if names[j] < names[i] {
				names[i], names[j] = names[j], names[i]
			}
		}
	}
	out := make([][]byte, len(names))
	for i, name := range names {
		out[i] = classes[name]
	}
	return out
}

func verifyM4dAssertNoOpcode(t *testing.T, classes map[string][]byte, opcode byte) {
	t.Helper()
	for name, classfile := range classes {
		for _, method := range parseStaticsClass(t, classfile).methods {
			if bytes.IndexByte(method.code, opcode) >= 0 {
				t.Fatalf("trusted class %s method %s%s contains excluded opcode 0x%02x: %x", name, method.name, method.descriptor, opcode, method.code)
			}
		}
	}
}

func verifyM4dAssertDeclaredClass(t *testing.T, classfile []byte, want string) {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	entry := c.entry(t, c.thisClass)
	if entry.tag != 7 {
		t.Fatalf("this_class tag=%d, want Class", entry.tag)
	}
	if got := c.utf8[c.u2(t, entry.offset+1)]; got != want {
		t.Fatalf("declared class=%q, want %q", got, want)
	}
}

func verifyM4dAnewarraySite(t *testing.T, classfile []byte, method string) (int, string) {
	t.Helper()
	c := parseStaticsClass(t, classfile)
	m := c.namedMethod(t, method)
	pc := verifyM4dOpcodePC(t, m.code, verifyM4dAnewarray, 0)
	if pc+2 >= len(m.code) {
		t.Fatalf("truncated verifier fixture anewarray at pc %d", pc)
	}
	index := binary.BigEndian.Uint16(m.code[pc+1:])
	e := c.entry(t, index)
	if e.tag != 7 {
		t.Fatalf("fixture anewarray CP tag=%d, want Class", e.tag)
	}
	return pc, c.utf8[c.u2(t, e.offset+1)]
}

func verifyM4dClassIndex(t *testing.T, c staticsClass, name string) uint16 {
	t.Helper()
	for i := 1; i < len(c.entries); i++ {
		e := c.entries[i]
		if e.tag == 7 && c.utf8[c.u2(t, e.offset+1)] == name {
			return uint16(i)
		}
	}
	t.Fatalf("Class constant %q missing", name)
	return 0
}

func verifyM4dMemberInstruction(t *testing.T, c staticsClass, m staticsMethod, opcode byte, name, descriptor string) (uint16, int) {
	t.Helper()
	for pc := 0; pc+2 < len(m.code); pc++ {
		if m.code[pc] != opcode {
			continue
		}
		ref := binary.BigEndian.Uint16(m.code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 10 {
			continue
		}
		e := c.entry(t, ref)
		nat := c.entry(t, c.u2(t, e.offset+3))
		if nat.tag == 12 && c.utf8[c.u2(t, nat.offset+1)] == name && c.utf8[c.u2(t, nat.offset+3)] == descriptor {
			return ref, pc
		}
	}
	t.Fatalf("%s%s lacks opcode 0x%02x for %s%s: %x", m.name, m.descriptor, opcode, name, descriptor, m.code)
	return 0, 0
}

func verifyM4dOpcodePC(t *testing.T, code []byte, opcode byte, occurrence int) int {
	t.Helper()
	seen := 0
	for pc, op := range code {
		if op == opcode {
			if seen == occurrence {
				return pc
			}
			seen++
		}
	}
	t.Fatalf("opcode 0x%02x occurrence %d missing from %x", opcode, occurrence, code)
	return -1
}

func verifyM4dMutate(t *testing.T, original []byte, change func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	change(out, parseStaticsClass(t, out))
	return out
}

func verifyM4dAppendClassForExistingName(t *testing.T, original []byte, name string) ([]byte, uint16) {
	t.Helper()
	c := parseStaticsClass(t, original)
	nameIndex := c.utfIndex(t, name)
	if c.cpCount >= 65535 {
		t.Fatal("test constant pool full")
	}
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	return out, uint16(c.cpCount)
}

func verifyM4dRetargetAnewarrayToAppendedName(t *testing.T, original []byte, method, name string) []byte {
	t.Helper()
	c := parseStaticsClass(t, original)
	if c.cpCount+2 > 65535 || len(name) > 65535 {
		t.Fatal("test CP/name too large")
	}
	utf := make([]byte, 3+len(name))
	utf[0] = 1
	binary.BigEndian.PutUint16(utf[1:], uint16(len(name)))
	copy(utf[3:], name)
	class := []byte{7, byte(c.cpCount >> 8), byte(c.cpCount)}
	insert := append(utf, class...)
	out := make([]byte, len(original)+len(insert))
	copy(out, original[:c.cpEnd])
	copy(out[c.cpEnd:], insert)
	copy(out[c.cpEnd+len(insert):], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+2))
	parsed := parseStaticsClass(t, out)
	m := parsed.namedMethod(t, method)
	pc := verifyM4dOpcodePC(t, m.code, verifyM4dAnewarray, 0)
	binary.BigEndian.PutUint16(m.code[pc+1:], uint16(c.cpCount+1))
	return out
}

func verifyM4dRewriteCode(t *testing.T, original []byte, name, descriptor string, code []byte) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	if len(code) > len(m.code) {
		t.Fatalf("replacement %s%s has %d bytes, Code has %d", name, descriptor, len(code), len(m.code))
	}
	start := -1
	for i := range out {
		if len(m.code) > 0 && &out[i] == &m.code[0] {
			start = i
			break
		}
	}
	if start < 8 {
		t.Fatalf("cannot locate Code for %s%s", name, descriptor)
	}
	binary.BigEndian.PutUint16(out[start-8:], 16)
	binary.BigEndian.PutUint16(out[start-6:], 16)
	for i := range m.code {
		m.code[i] = 0
	}
	copy(m.code, code)
	return out
}

func verifyM4dRewriteAtEnd(t *testing.T, original []byte, name, descriptor string, opcode byte) []byte {
	t.Helper()
	out := verifyM4dRewriteCode(t, original, name, descriptor, nil)
	m := parseStaticsClass(t, out).method(t, name, descriptor)
	m.code[len(m.code)-1] = opcode
	return out
}

func verifyM4dReplaceOpcode(t *testing.T, original []byte, method string, from, to byte) ([]byte, int) {
	t.Helper()
	pc := verifyM4dOpcodePC(t, parseStaticsClass(t, original).namedMethod(t, method).code, from, 0)
	out := verifyM4dMutate(t, original, func(_ []byte, c staticsClass) {
		c.namedMethod(t, method).code[pc] = to
	})
	return out, pc
}

func verifyM4dAssertValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil || result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result/error=%+v/%v, want value %d", result, err, want)
	}
}

func verifyM4dAssertException(t *testing.T, run func() (Result, error), want string, kind byte) {
	t.Helper()
	result, err := run()
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if err != nil || result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("result/error=%+v/%v data=%x, want exact %s kind %d", result, err, result.RevertData, want, kind)
	}
}

func verifyM4dAssertMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want MethodError(%d)", result, err, code)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 ||
		!bytes.Equal(result.RevertData[:4], selector) || verifyM4dUint256(t, result.RevertData[4:]) != code {
		t.Fatalf("result=%+v data=%x, want exact MethodError(%d)", result, result.RevertData, code)
	}
}

func verifyM4dAssertError(t *testing.T, run func() (Result, error), signature string, code, pc uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error=%+v/%v, want %s(%d,%d)", result, err, signature, code, pc)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result=%+v data=%x, want exact %s payload", result, result.RevertData, signature)
	}
	if got := verifyM4dUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code=%d want %d data=%x", signature, got, code, result.RevertData)
	}
	if got := verifyM4dUint256(t, result.RevertData[36:]); got != pc {
		t.Fatalf("%s pc=%d want %d data=%x", signature, got, pc, result.RevertData)
	}
}

func verifyM4dUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical uint256 %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}
