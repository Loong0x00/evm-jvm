// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"errors"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const staticsValidationGasLimit = uint64(90_000_000)

// These tests compile only trusted inline Java. Every malformed input starts as
// valid javac --release 8 output and is then changed by a narrow test-only
// mutation. Instruction locations are obtained from the original method Code,
// before a CP or member mutation, so each negative has an explicit PC plan.
func TestM3cStaticInitializationStateAndOperandPreservation(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"state/Root.java": `package state; public final class Root {
			static int zero;
			static int count;
			static int self = initialize();
			static int initialize() { count = count + 1; return zero * 10 + count; }
			public static int root(int x) {
				int before = count;
				zero = x;
				return self * 1000 + before * 100 + count * 10 + zero;
			}
			public static int getOperand() { return 1000 + Target.value; }
			public static int putOperand(int x) {
				int assigned = (Target.value = x + 3);
				return assigned * 100 + Target.value;
			}
			public static int callsOnce() { return Target.read() * 10 + Target.read(); }
		}`,
		"state/Target.java": `package state; public final class Target {
			static int starts;
			static int value = start();
			static int start() { starts = starts + 1; return 7; }
			static int read() { return starts; }
		}`,
	}, "state/Root", "state/Target")
	inputs := [][]byte{classes["state/Target"], classes["state/Root"]}

	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(inputs, "state/Root", "root", []int32{6}, staticsValidationGasLimit)
	}, 1116)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(inputs, "state/Root", "getOperand", nil, staticsValidationGasLimit)
	}, 1007)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(inputs, "state/Root", "putOperand", []int32{8}, staticsValidationGasLimit)
	}, 1111)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(inputs, "state/Root", "callsOnce", nil, staticsValidationGasLimit)
	}, 11)
}

func TestM3cInitializationOrderCyclesIsolationAndNoEagerInitialization(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"cycle/Root.java": `package cycle; public final class Root {
			public static int firstA() { return A.x * 10 + B.y; }
			public static int firstB() { return B.y * 10 + A.x; }
			public static int isolated() { return left.Same.value * 10 + right.Same.value; }
			public static int ignoreUnused() { return 9; }
			public static int inlineConstant() { return ConstantHolder.VALUE; }
		}`,
		"cycle/A.java": `package cycle; public final class A { static int x = B.y + 1; }`,
		"cycle/B.java": `package cycle; public final class B { static int y = A.x + 2; }`,
		"cycle/Unused.java": `package cycle; public final class Unused {
			static int bad = 1 / 0; public static int read() { return bad; }
		}`,
		"cycle/ConstantHolder.java": `package cycle; public final class ConstantHolder {
			public static final int VALUE = 17;
			static int bad = 1 / 0;
		}`,
		"left/Same.java":  `package left; public final class Same { public static int value = 4; }`,
		"right/Same.java": `package right; public final class Same { public static int value = 7; }`,
	}, "cycle/Root", "cycle/A", "cycle/B", "cycle/Unused", "cycle/ConstantHolder", "left/Same", "right/Same")
	orderA := []string{"cycle/Unused", "right/Same", "cycle/B", "cycle/Root", "left/Same", "cycle/ConstantHolder", "cycle/A"}
	orderB := []string{"cycle/A", "cycle/ConstantHolder", "left/Same", "cycle/Root", "cycle/B", "right/Same", "cycle/Unused"}
	bundle := func(order []string) [][]byte {
		out := make([][]byte, len(order))
		for i, name := range order {
			out[i] = classes[name]
		}
		return out
	}
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(bundle(orderA), "cycle/Root", "firstA", nil, staticsValidationGasLimit)
	}, 32)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(bundle(orderB), "cycle/Root", "firstB", nil, staticsValidationGasLimit)
	}, 31)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(bundle(orderA), "cycle/Root", "isolated", nil, staticsValidationGasLimit)
	}, 47)
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(bundle(orderB), "cycle/Root", "ignoreUnused", nil, staticsValidationGasLimit)
	}, 9)
	// javac inlines VALUE, so merely supplying ConstantHolder must not initialize it.
	assertStaticsValue(t, func() (Result, error) {
		return RunClasses(bundle(orderA), "cycle/Root", "inlineConstant", nil, staticsValidationGasLimit)
	}, 17)
}

func TestM3cEachRunGetsFreshStaticStorage(t *testing.T) {
	classfile := compileJava(t, "FreshStatics", `public final class FreshStatics {
		static int count = initial();
		static int initial() { return count + 1; }
		public static int run() { count = count + 1; return count; }
	}`)
	for invocation := 0; invocation < 2; invocation++ {
		assertStaticsValue(t, func() (Result, error) {
			return Run(classfile, "run", nil, staticsValidationGasLimit)
		}, 2)
	}
}

func TestM3cConstantValuePreparationRules(t *testing.T) {
	t.Run("static-without-final-and-forced-getstatic", func(t *testing.T) {
		original := compileJava(t, "ConstantNoFinal", `public final class ConstantNoFinal {
			public static final int CONSTANT = 37;
			public static int probe;
			public static int run() { return probe; }
		}`)
		classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
			constant := c.field(t, "CONSTANT", "I")
			binary.BigEndian.PutUint16(out[constant.accessOffset:], constant.access&^accFinal)
			ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
			nat := c.u2(t, c.entry(t, ref).offset+3)
			binary.BigEndian.PutUint16(out[c.entry(t, nat).offset+1:], c.utfIndex(t, "CONSTANT"))
		})
		// The CP mutation is valid and forces a true getstatic; javac would inline
		// a direct source reference to CONSTANT.
		assertStaticsValue(t, func() (Result, error) {
			return Run(classfile, "run", nil, staticsValidationGasLimit)
		}, 37)
	})

	t.Run("instance-constantvalue-is-ignored", func(t *testing.T) {
		classfile := compileJava(t, "InstanceConstant", `public final class InstanceConstant {
			final int instance = 23;
			static int marker;
			public static int run() { return marker; }
		}`)
		instance := parseStaticsClass(t, classfile).field(t, "instance", "I")
		if instance.access&accStatic != 0 || instance.attribute(t, "ConstantValue") == nil {
			t.Fatalf("javac fixture must have a nonstatic ConstantValue field: %+v", instance)
		}
		assertStaticsValue(t, func() (Result, error) {
			return Run(classfile, "run", nil, staticsValidationGasLimit)
		}, 0)
	})

	t.Run("final-write-in-actual-clinit", func(t *testing.T) {
		classfile := compileJava(t, "FinalInClinit", `public final class FinalInClinit {
			static final int value;
			static { value = 29; }
			public static int run() { return value; }
		}`)
		assertStaticsValue(t, func() (Result, error) {
			return Run(classfile, "run", nil, staticsValidationGasLimit)
		}, 29)
	})
}

func TestM3cFieldError1RejectsMalformedFieldrefsAtInstructionPC(t *testing.T) {
	original := compileJava(t, "FieldShape", `public final class FieldShape {
		static int value;
		static long wide;
		public static int run() { return value; }
	}`)
	_, wantPC := parseStaticsClass(t, original).fieldInstruction(t, "run", opGetstatic, 0)
	cases := map[string]func() []byte{
		"operand-zero": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				_, pc := c.fieldInstruction(t, "run", opGetstatic, 0)
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], 0)
			})
		},
		"operand-out-of-range": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				_, pc := c.fieldInstruction(t, "run", opGetstatic, 0)
				binary.BigEndian.PutUint16(c.method(t, "run", "()I").code[pc+1:], uint16(c.cpCount))
			})
		},
		"fieldref-tag": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				out[c.entry(t, ref).offset] = 10
			})
		},
		"class-index": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], 0)
			})
		},
		"class-tag": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				nat := c.u2(t, c.entry(t, ref).offset+3)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], nat)
			})
		},
		"name-and-type-index": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+3:], 0)
			})
		},
		"name-and-type-tag": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				owner := c.u2(t, c.entry(t, ref).offset+1)
				binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+3:], owner)
			})
		},
		"field-name-utf8": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				nat := c.u2(t, c.entry(t, ref).offset+3)
				binary.BigEndian.PutUint16(out[c.entry(t, nat).offset+1:], ref)
			})
		},
		"descriptor-utf8": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				nat := c.u2(t, c.entry(t, ref).offset+3)
				binary.BigEndian.PutUint16(out[c.entry(t, nat).offset+3:], nat)
			})
		},
		"owner-utf8-index": func() []byte {
			return duplicateStaticsFieldOwner(t, original, "run", 0, func(out []byte, c staticsClass, owner uint16) {
				binary.BigEndian.PutUint16(out[c.entry(t, owner).offset+1:], 0)
			})
		},
		"owner-utf8-tag": func() []byte {
			return duplicateStaticsFieldOwner(t, original, "run", 0, func(out []byte, c staticsClass, owner uint16) {
				ref, _ := c.fieldInstruction(t, "run", opGetstatic, 0)
				binary.BigEndian.PutUint16(out[c.entry(t, owner).offset+1:], ref)
			})
		},
	}
	for name, makeClass := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := makeClass()
			assertStaticsError(t, func() (Result, error) {
				return Run(classfile, "run", nil, staticsValidationGasLimit)
			}, "FieldError(uint256,uint256)", 1, uint64(wantPC))
		})
	}
}

func TestM3cFieldResolutionErrorCodesAndMissingOwner(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"fields/Root.java": `package fields; public final class Root {
			public static int read() { return Target.value; }
			public static int write(int x) { Target.value = x; return x; }
			public static int narrow() { return Target.narrow; }
			public static int wide() { return (int)Target.wide; }
		}`,
		"fields/Target.java": `package fields; public final class Target {
			public static int value;
			public static byte narrow;
			public static long wide;
		}`,
	}, "fields/Root", "fields/Target")
	root := classes["fields/Root"]
	_, readPC := parseStaticsClass(t, root).fieldInstruction(t, "read", opGetstatic, 0)

	t.Run("missing-field", func(t *testing.T) {
		mutated := mutateStaticsClass(t, root, func(out []byte, c staticsClass) {
			ref, _ := c.fieldInstruction(t, "read", opGetstatic, 0)
			nat := c.u2(t, c.entry(t, ref).offset+3)
			binary.BigEndian.PutUint16(out[c.entry(t, nat).offset+1:], c.utfIndex(t, "fields/Target"))
		})
		assertStaticsError(t, func() (Result, error) {
			return RunClasses([][]byte{classes["fields/Target"], mutated}, "fields/Root", "read", nil, staticsValidationGasLimit)
		}, "FieldError(uint256,uint256)", 2, uint64(readPC))
	})

	t.Run("nonstatic", func(t *testing.T) {
		target := mutateStaticsClass(t, classes["fields/Target"], func(out []byte, c staticsClass) {
			field := c.field(t, "value", "I")
			binary.BigEndian.PutUint16(out[field.accessOffset:], field.access&^accStatic)
		})
		assertStaticsError(t, func() (Result, error) {
			return RunClasses([][]byte{root, target}, "fields/Root", "read", nil, staticsValidationGasLimit)
		}, "FieldError(uint256,uint256)", 3, uint64(readPC))
	})

	t.Run("byte-descriptor-default-zero", func(t *testing.T) {
		parsed := parseStaticsClass(t, root)
		code := parsed.method(t, "narrow", "()I").code
		if len(code) != 4 || code[0] != opGetstatic || code[3] != 0xac {
			t.Fatalf("narrow bytecode = %x, want getstatic <B field>; ireturn", code)
		}
		// The unselected wide method below contains unsupported l2i, but must not
		// interfere with verification of this narrow method's field resolution.
		assertStaticsValue(t, func() (Result, error) {
			return RunClasses([][]byte{root, classes["fields/Target"]}, "fields/Root", "narrow", nil, staticsValidationGasLimit)
		}, 0)
	})

	t.Run("long-descriptor-default-zero-converts-to-int", func(t *testing.T) {
		parsed := parseStaticsClass(t, root)
		_, getstaticPC := parsed.fieldInstruction(t, "wide", opGetstatic, 0)
		code := parsed.method(t, "wide", "()I").code
		if len(code) != 5 || getstaticPC != 0 || code[3] != 0x88 || code[4] != 0xac {
			t.Fatalf("wide bytecode = %x, want getstatic at PC 0; l2i at PC 3; ireturn", code)
		}
		bundle := [][]byte{root, classes["fields/Target"]}
		verifyM5baJava8Outcome(t, bundle, "fields.Root", "wide", nil, "value=0")
		assertStaticsValue(t, func() (Result, error) {
			return RunClasses(bundle, "fields/Root", "wide", nil, staticsValidationGasLimit)
		}, 0)
	})

	t.Run("missing-owner-is-link-error", func(t *testing.T) {
		missing := compileBundleValidationJava(t, map[string]string{
			"missingfield/Root.java": `package missingfield; public final class Root {
				public static int run() { return Owner.value; }
			}`,
			"missingfield/Owner.java": `package missingfield; public final class Owner { public static int value; }`,
		}, "missingfield/Root", "missingfield/Owner")
		_, pc := parseStaticsClass(t, missing["missingfield/Root"]).fieldInstruction(t, "run", opGetstatic, 0)
		assertStaticsError(t, func() (Result, error) {
			return RunClasses([][]byte{missing["missingfield/Root"]}, "missingfield/Root", "run", nil, staticsValidationGasLimit)
		}, "LinkError(uint256,uint256)", 4, uint64(pc))
	})
}

func TestM3cFieldAccessAndFinalWritesUseFieldError4(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"accessfield/Root.java": `package accessfield; import targetfield.Target; public final class Root {
			public static int read() { return Target.value; }
			public static int write(int x) { Target.value = x; return x; }
			public static int cached(int x) { int before = Target.value; Target.value = x; return before; }
		}`,
		"targetfield/Target.java": `package targetfield; public final class Target { public static int value; }`,
	}, "accessfield/Root", "targetfield/Target")
	root := classes["accessfield/Root"]
	read := parseStaticsClass(t, root)
	_, readPC := read.fieldInstruction(t, "read", opGetstatic, 0)
	_, writePC := read.fieldInstruction(t, "write", opPutstatic, 0)
	_, cachedPutPC := read.fieldInstruction(t, "cached", opPutstatic, 0)

	cases := []struct {
		name   string
		method string
		args   []int32
		pc     int
		mutate func([]byte, staticsClass)
	}{
		{"private-field", "read", nil, readPC, func(out []byte, c staticsClass) {
			f := c.field(t, "value", "I")
			binary.BigEndian.PutUint16(out[f.accessOffset:], (f.access&^accessMask)|accPrivate|accStatic)
		}},
		{"package-field", "read", nil, readPC, func(out []byte, c staticsClass) {
			f := c.field(t, "value", "I")
			binary.BigEndian.PutUint16(out[f.accessOffset:], (f.access&^accessMask)|accStatic)
		}},
		{"nonpublic-owner", "read", nil, readPC, func(out []byte, c staticsClass) {
			flags := binary.BigEndian.Uint16(out[c.cpEnd:]) &^ accPublic
			binary.BigEndian.PutUint16(out[c.cpEnd:], flags)
		}},
		{"final-write", "write", []int32{4}, writePC, func(out []byte, c staticsClass) {
			f := c.field(t, "value", "I")
			binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accFinal)
		}},
		// A successful getstatic may cache identity/resolution, but cannot cache
		// permission for the later putstatic at a different instruction PC.
		{"cached-read-then-final-write", "cached", []int32{4}, cachedPutPC, func(out []byte, c staticsClass) {
			f := c.field(t, "value", "I")
			binary.BigEndian.PutUint16(out[f.accessOffset:], f.access|accFinal)
		}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			target := mutateStaticsClass(t, classes["targetfield/Target"], tc.mutate)
			assertStaticsError(t, func() (Result, error) {
				return RunClasses([][]byte{target, root}, "accessfield/Root", tc.method, tc.args, staticsValidationGasLimit)
			}, "FieldError(uint256,uint256)", 4, uint64(tc.pc))
		})
	}
}

func TestM3cHelperCalledByClinitCannotWriteFinal(t *testing.T) {
	original := compileJava(t, "HelperFinal", `public final class HelperFinal {
		static int value;
		static { helper(); }
		static void helper() { value = 7; }
		public static int run() { return value; }
	}`)
	parsed := parseStaticsClass(t, original)
	_, putPC := parsed.fieldInstruction(t, "helper", opPutstatic, 0)
	classfile := mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
		field := c.field(t, "value", "I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], field.access|accFinal)
	})
	assertStaticsError(t, func() (Result, error) {
		return Run(classfile, "run", nil, staticsValidationGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(putPC))
}

func TestM3cMalformedConstantValueUsesFieldError5AndFieldIndex(t *testing.T) {
	original := compileJava(t, "ConstantShape", `public final class ConstantShape {
		static final int VALUE = 41;
		static int probe;
		public static int run() { return probe; }
	}`)
	parsed := parseStaticsClass(t, original)
	field := parsed.field(t, "VALUE", "I")
	constant := field.attribute(t, "ConstantValue")
	if constant == nil || constant.length != 2 {
		t.Fatalf("unexpected javac ConstantValue attribute: %+v", constant)
	}
	location := uint64(field.index)
	cases := map[string]func() []byte{
		"ill-sized": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				a := c.field(t, "VALUE", "I").attribute(t, "ConstantValue")
				binary.BigEndian.PutUint32(out[a.lengthOffset:], 1)
			})
		},
		"zero-index": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				a := c.field(t, "VALUE", "I").attribute(t, "ConstantValue")
				binary.BigEndian.PutUint16(out[a.dataOffset:], 0)
			})
		},
		"out-of-range-index": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				a := c.field(t, "VALUE", "I").attribute(t, "ConstantValue")
				binary.BigEndian.PutUint16(out[a.dataOffset:], uint16(c.cpCount))
			})
		},
		"wrong-tag": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				a := c.field(t, "VALUE", "I").attribute(t, "ConstantValue")
				binary.BigEndian.PutUint16(out[a.dataOffset:], c.utfIndex(t, "VALUE"))
			})
		},
		"duplicate": func() []byte {
			return duplicateConstantValueAttribute(t, original, "VALUE", "I")
		},
	}
	for name, makeClass := range cases {
		t.Run(name, func(t *testing.T) {
			classfile := makeClass()
			assertStaticsError(t, func() (Result, error) {
				return Run(classfile, "run", nil, staticsValidationGasLimit)
			}, "FieldError(uint256,uint256)", 5, location)
		})
	}
}

func TestM3cInvalidInitializerMetadataUsesInitError1AndBundleClassIndex(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"badinit/Root.java": `package badinit; public final class Root {
			public static int run() { return Target.read(); }
		}`,
		"badinit/Target.java": `package badinit; public final class Target {
			static int value = 3;
			static void spare() { }
			public static int read() { return value; }
		}`,
	}, "badinit/Root", "badinit/Target")
	original := classes["badinit/Target"]
	cases := map[string]func() []byte{
		"bad-signature": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				m := c.method(t, "<clinit>", "()V")
				binary.BigEndian.PutUint16(out[m.descriptorIndexOffset:], c.utfIndex(t, "()I"))
			})
		},
		"nonstatic": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				m := c.method(t, "<clinit>", "()V")
				binary.BigEndian.PutUint16(out[m.accessOffset:], m.access&^accStatic)
			})
		},
		"native": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				m := c.method(t, "<clinit>", "()V")
				binary.BigEndian.PutUint16(out[m.accessOffset:], m.access|accNative)
			})
		},
		"missing-code": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				m := c.method(t, "<clinit>", "()V")
				binary.BigEndian.PutUint16(out[m.codeNameOffset:], c.utfIndex(t, "SourceFile"))
			})
		},
		"duplicate": func() []byte {
			return mutateStaticsClass(t, original, func(out []byte, c staticsClass) {
				m := c.method(t, "spare", "()V")
				binary.BigEndian.PutUint16(out[m.nameIndexOffset:], c.utfIndex(t, "<clinit>"))
			})
		},
	}
	for name, makeTarget := range cases {
		t.Run(name, func(t *testing.T) {
			target := makeTarget()
			assertStaticsError(t, func() (Result, error) {
				// Target is deliberately input index 1; InitError location is a
				// bundle class index, never the invokestatic PC in Root.
				return RunClasses([][]byte{classes["badinit/Root"], target}, "badinit/Root", "run", nil, staticsValidationGasLimit)
			}, "InitError(uint256,uint256)", 1, 1)
		})
	}
}

func TestM3cInitializerJavaOutcomesKeepWrappingBoundaryAndOOGDistinct(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"outcomes/Outside.java": `package outcomes; public final class Outside {
			public static int run(int x) { return 9 / x; }
		}`,
		"outcomes/InitArithmetic.java": `package outcomes; public final class InitArithmetic {
			static int value = helper();
			static int helper() { return 9 / 0; }
			public static int run() { return value; }
		}`,
		"outcomes/InitOverflow.java": `package outcomes; public final class InitOverflow {
			static int value = recurse();
			static int recurse() { return recurse(); }
			public static int run() { return value; }
		}`,
		"outcomes/Driver.java": `package outcomes; public final class Driver {
			public static int run() { return InitArithmetic.run(); }
		}`,
	}, "outcomes/Outside", "outcomes/InitArithmetic", "outcomes/InitOverflow", "outcomes/Driver")
	assertStaticsException(t, func() (Result, error) {
		return Run(classes["outcomes/Outside"], "run", []int32{0}, staticsValidationGasLimit)
	}, "java.lang.ArithmeticException")
	// The same ArithmeticException is wrapped whether the failing initializer
	// belongs to the root class or to a callee reached by invokestatic.
	assertStaticsException(t, func() (Result, error) {
		return Run(classes["outcomes/InitArithmetic"], "run", nil, staticsValidationGasLimit)
	}, "java.lang.ExceptionInInitializerError")
	assertStaticsException(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["outcomes/Driver"], classes["outcomes/InitArithmetic"]},
			"outcomes/Driver", "run", nil, staticsValidationGasLimit,
		)
	}, "java.lang.ExceptionInInitializerError")
	assertStaticsException(t, func() (Result, error) {
		return Run(classes["outcomes/InitOverflow"], "run", nil, staticsValidationGasLimit)
	}, "java.lang.StackOverflowError")

	result, err := Run(classes["outcomes/InitArithmetic"], "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) {
		t.Fatalf("result/error = %+v/%v, want true EVM out of gas", result, err)
	}
	if result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("out of gas was misclassified as Java outcome: %+v", result)
	}
}

func assertStaticsValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("EVM execution failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want value %d with measured successful execution", result, want)
	}
}

func assertStaticsException(t *testing.T, run func() (Result, error), want string) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("Java outcome returned EVM failure: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != want || result.GasUsed == 0 || len(result.RevertData) != 36 {
		t.Fatalf("result = %+v, want exact Java outcome %s", result, want)
	}
	selector := crypto.Keccak256([]byte("JavaException(uint256)"))[:4]
	if !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("Java outcome selector = %x, want %x", result.RevertData[:4], selector)
	}
	kind := map[string]byte{
		"java.lang.ArithmeticException":         1,
		"java.lang.StackOverflowError":          2,
		"java.lang.ExceptionInInitializerError": 3,
	}[want]
	if kind == 0 || !bytes.Equal(result.RevertData[4:35], make([]byte, 31)) || result.RevertData[35] != kind {
		t.Fatalf("Java outcome payload = %x, want kind %d", result.RevertData, kind)
	}
}

func assertStaticsError(t *testing.T, run func() (Result, error), signature string, code, location uint64) {
	t.Helper()
	result, err := run()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact %s revert", result, err, signature)
	}
	selector := crypto.Keccak256([]byte(signature))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 68 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact %s payload", result, signature)
	}
	if got := staticsUint256(t, result.RevertData[4:36]); got != code {
		t.Fatalf("%s code = %d, want %d (data=%x)", signature, got, code, result.RevertData)
	}
	if got := staticsUint256(t, result.RevertData[36:68]); got != location {
		t.Fatalf("%s location = %d, want %d (data=%x)", signature, got, location, result.RevertData)
	}
}

func staticsUint256(t *testing.T, word []byte) uint64 {
	t.Helper()
	if len(word) != 32 || !bytes.Equal(word[:24], make([]byte, 24)) {
		t.Fatalf("noncanonical or oversized uint256 word: %x", word)
	}
	return binary.BigEndian.Uint64(word[24:])
}

const (
	opGetstatic = byte(0xb2)
	opPutstatic = byte(0xb3)
	accPublic   = uint16(0x0001)
	accPrivate  = uint16(0x0002)
	accStatic   = uint16(0x0008)
	accFinal    = uint16(0x0010)
	accNative   = uint16(0x0100)
	accessMask  = uint16(0x0001 | 0x0002 | 0x0004)
)

type staticsCPEntry struct {
	tag    byte
	offset int
}

type staticsAttribute struct {
	name         string
	nameOffset   int
	length       uint32
	lengthOffset int
	dataOffset   int
	end          int
}

type staticsField struct {
	index           int
	access          uint16
	accessOffset    int
	name            string
	descriptor      string
	attributesCount uint16
	attrsCountOff   int
	attributes      []staticsAttribute
	end             int
}

func (f staticsField) attribute(t *testing.T, name string) *staticsAttribute {
	t.Helper()
	for i := range f.attributes {
		if f.attributes[i].name == name {
			return &f.attributes[i]
		}
	}
	return nil
}

type staticsMethod struct {
	access                uint16
	accessOffset          int
	name                  string
	nameIndexOffset       int
	descriptor            string
	descriptorIndexOffset int
	codeNameOffset        int
	code                  []byte
}

type staticsClass struct {
	data      []byte
	cpCount   int
	cpEnd     int
	entries   []staticsCPEntry
	utf8      map[uint16]string
	fields    []staticsField
	methods   []staticsMethod
	thisClass uint16
}

func parseStaticsClass(t *testing.T, data []byte) staticsClass {
	t.Helper()
	pos := 0
	need := func(n int) {
		if n < 0 || pos < 0 || pos+n > len(data) {
			t.Fatalf("truncated test class at offset %d, need %d", pos, n)
		}
	}
	u1 := func() byte { need(1); v := data[pos]; pos++; return v }
	u2 := func() uint16 { need(2); v := binary.BigEndian.Uint16(data[pos:]); pos += 2; return v }
	u4 := func() uint32 { need(4); v := binary.BigEndian.Uint32(data[pos:]); pos += 4; return v }
	skip := func(n int) { need(n); pos += n }
	if len(data) < 10 || binary.BigEndian.Uint32(data[:4]) != 0xcafebabe {
		t.Fatal("javac fixture has bad magic")
	}
	pos = 8
	cpCount := int(u2())
	c := staticsClass{data: data, cpCount: cpCount, entries: make([]staticsCPEntry, cpCount), utf8: make(map[uint16]string)}
	for i := 1; i < cpCount; i++ {
		offset := pos
		tag := u1()
		c.entries[i] = staticsCPEntry{tag: tag, offset: offset}
		switch tag {
		case 1:
			n := int(u2())
			need(n)
			c.utf8[uint16(i)] = string(data[pos : pos+n])
			skip(n)
		case 3, 4, 9, 10, 11, 12, 17, 18:
			skip(4)
		case 5, 6:
			skip(8)
			i++
		case 7, 8, 16, 19, 20:
			skip(2)
		case 15:
			skip(3)
		default:
			t.Fatalf("unknown test constant-pool tag %d", tag)
		}
	}
	c.cpEnd = pos
	skip(2)
	c.thisClass = u2()
	skip(2)
	for n := int(u2()); n > 0; n-- {
		skip(2)
	}
	readAttrs := func() ([]staticsAttribute, uint16, int) {
		countOffset := pos
		count := u2()
		attrs := make([]staticsAttribute, 0, count)
		for i := 0; i < int(count); i++ {
			nameOffset := pos
			nameIndex := u2()
			lengthOffset := pos
			length := u4()
			dataOffset := pos
			skip(int(length))
			attrs = append(attrs, staticsAttribute{
				name: c.utf8[nameIndex], nameOffset: nameOffset, length: length,
				lengthOffset: lengthOffset, dataOffset: dataOffset, end: pos,
			})
		}
		return attrs, count, countOffset
	}
	fieldCount := int(u2())
	for i := 0; i < fieldCount; i++ {
		accessOffset := pos
		access := u2()
		nameIndex, descriptorIndex := u2(), u2()
		attrs, count, countOffset := readAttrs()
		c.fields = append(c.fields, staticsField{
			index: i, access: access, accessOffset: accessOffset,
			name: c.utf8[nameIndex], descriptor: c.utf8[descriptorIndex],
			attributesCount: count, attrsCountOff: countOffset, attributes: attrs, end: pos,
		})
	}
	methodCount := int(u2())
	for i := 0; i < methodCount; i++ {
		accessOffset := pos
		access := u2()
		nameIndexOffset := pos
		nameIndex := u2()
		descriptorIndexOffset := pos
		descriptorIndex := u2()
		attrs, _, _ := readAttrs()
		method := staticsMethod{
			access: access, accessOffset: accessOffset,
			name: c.utf8[nameIndex], nameIndexOffset: nameIndexOffset,
			descriptor: c.utf8[descriptorIndex], descriptorIndexOffset: descriptorIndexOffset,
			codeNameOffset: -1,
		}
		for _, attr := range attrs {
			if attr.name != "Code" {
				continue
			}
			if attr.length < 8 || attr.dataOffset+8 > len(data) {
				t.Fatal("invalid test Code attribute")
			}
			codeLength := int(binary.BigEndian.Uint32(data[attr.dataOffset+4:]))
			if codeLength < 1 || 8+codeLength > int(attr.length) {
				t.Fatal("invalid test Code length")
			}
			method.codeNameOffset = attr.nameOffset
			method.code = data[attr.dataOffset+8 : attr.dataOffset+8+codeLength]
		}
		c.methods = append(c.methods, method)
	}
	return c
}

func (c staticsClass) entry(t *testing.T, index uint16) staticsCPEntry {
	t.Helper()
	if index == 0 || int(index) >= len(c.entries) || c.entries[index].tag == 0 {
		t.Fatalf("invalid test CP index %d", index)
	}
	return c.entries[index]
}

func (c staticsClass) u2(t *testing.T, offset int) uint16 {
	t.Helper()
	if offset < 0 || offset+2 > len(c.data) {
		t.Fatalf("invalid test u2 offset %d", offset)
	}
	return binary.BigEndian.Uint16(c.data[offset:])
}

func (c staticsClass) utfIndex(t *testing.T, value string) uint16 {
	t.Helper()
	for index, text := range c.utf8 {
		if text == value {
			return index
		}
	}
	t.Fatalf("test UTF8 %q not found", value)
	return 0
}

func (c staticsClass) field(t *testing.T, name, descriptor string) staticsField {
	t.Helper()
	for _, field := range c.fields {
		if field.name == name && field.descriptor == descriptor {
			return field
		}
	}
	t.Fatalf("test field %s:%s not found", name, descriptor)
	return staticsField{}
}

func (c staticsClass) method(t *testing.T, name, descriptor string) staticsMethod {
	t.Helper()
	for _, method := range c.methods {
		if method.name == name && method.descriptor == descriptor {
			return method
		}
	}
	t.Fatalf("test method %s%s not found", name, descriptor)
	return staticsMethod{}
}

func (c staticsClass) namedMethod(t *testing.T, name string) staticsMethod {
	t.Helper()
	var found *staticsMethod
	for i := range c.methods {
		if c.methods[i].name == name {
			if found != nil {
				t.Fatalf("test method %q is overloaded", name)
			}
			found = &c.methods[i]
		}
	}
	if found == nil {
		t.Fatalf("test method %q not found", name)
	}
	return *found
}

func (c staticsClass) fieldInstruction(t *testing.T, method string, opcode byte, occurrence int) (uint16, int) {
	t.Helper()
	code := c.namedMethod(t, method).code
	seen := 0
	for pc := 0; pc+2 < len(code); pc++ {
		if code[pc] != opcode {
			continue
		}
		index := binary.BigEndian.Uint16(code[pc+1:])
		if index == 0 || int(index) >= len(c.entries) || c.entries[index].tag != 9 {
			continue
		}
		if seen == occurrence {
			return index, pc
		}
		seen++
	}
	t.Fatalf("method %q has no Fieldref opcode 0x%02x occurrence %d: %x", method, opcode, occurrence, code)
	return 0, 0
}

func mutateStaticsClass(t *testing.T, original []byte, mutate func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	mutate(out, parseStaticsClass(t, out))
	return out
}

func duplicateStaticsFieldOwner(t *testing.T, original []byte, method string, occurrence int, mutate func([]byte, staticsClass, uint16)) []byte {
	t.Helper()
	c := parseStaticsClass(t, original)
	ref, _ := c.fieldInstruction(t, method, opGetstatic, occurrence)
	refEntry := c.entry(t, ref)
	owner := c.u2(t, refEntry.offset+1)
	ownerEntry := c.entry(t, owner)
	if refEntry.tag != 9 || ownerEntry.tag != 7 || c.cpCount >= 65535 {
		t.Fatal("unexpected Fieldref/Class shape")
	}
	nameIndex := c.u2(t, ownerEntry.offset+1)
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	binary.BigEndian.PutUint16(out[refEntry.offset+1:], uint16(c.cpCount))
	parsed := parseStaticsClass(t, out)
	mutate(out, parsed, uint16(c.cpCount))
	return out
}

func duplicateConstantValueAttribute(t *testing.T, original []byte, name, descriptor string) []byte {
	t.Helper()
	c := parseStaticsClass(t, original)
	field := c.field(t, name, descriptor)
	attr := field.attribute(t, "ConstantValue")
	if attr == nil || attr.length != 2 {
		t.Fatal("test field lacks canonical ConstantValue")
	}
	insert := field.end
	out := make([]byte, len(original)+8)
	copy(out, original[:insert])
	binary.BigEndian.PutUint16(out[insert:], c.utfIndex(t, "ConstantValue"))
	binary.BigEndian.PutUint32(out[insert+2:], 2)
	copy(out[insert+6:], original[attr.dataOffset:attr.dataOffset+2])
	copy(out[insert+8:], original[insert:])
	binary.BigEndian.PutUint16(out[field.attrsCountOff:], field.attributesCount+1)
	return out
}
