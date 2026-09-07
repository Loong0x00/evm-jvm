// Copyright 2026 The go-ethereum Authors
// This file is part of go-ethereum.

package jvmevm

import (
	"bytes"
	"encoding/binary"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/core/vm"
	"github.com/ethereum/go-ethereum/crypto"
)

const hierarchyValidationGasLimit = uint64(100_000_000)

func TestM3dHierarchyError1MissingRequiredParentNeverUsesHostDisk(t *testing.T) {
	classes, outputDir := compileHierarchyValidationJava(t, map[string]string{
		"missing/Parent.java": `package missing; public class Parent { static int value = 8; }`,
		"missing/Child.java": `package missing; public final class Child extends Parent {
			public static int run() { return value; }
		}`,
		"missing/Independent.java": `package missing; public final class Independent {
			public static int run() { return 11; }
		}`,
	})
	parentOnDisk := filepath.Join(outputDir, "missing", "Parent.class")
	if _, err := os.Stat(parentOnDisk); err != nil {
		t.Fatalf("required parent must exist on host disk for fallback guard: %v", err)
	}

	// Only Child's raw bytes are supplied. The nearby javac output is deliberately
	// not an input and must never become an implicit host class path.
	result, err := RunClasses(
		[][]byte{classes["missing/Child"]}, "missing/Child", "run", nil,
		hierarchyValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 1, 0)

	// Linking is active-path based: an unentered class with an omitted parent does
	// not poison an independent root merely because both raw classes were supplied.
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["missing/Child"], classes["missing/Independent"]},
			"missing/Independent", "run", nil, hierarchyValidationGasLimit,
		)
	}, 11)
}

func TestM3dHierarchyError2CyclesReportFirstRepeatedBundleIndex(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"cycles/Solo.java": `package cycles; public class Solo { public static int run() { return 1; } }`,
		"cycles/Parent.java": `package cycles; public class Parent {
			static int mention() { return Child.flag; }
			public static int run() { return 2; }
		}`,
		"cycles/Child.java": `package cycles; public class Child extends Parent {
			static int flag;
			public static int childRun() { return 3; }
		}`,
	}, "cycles/Solo", "cycles/Parent", "cycles/Child")

	// The self edge uses a newly appended CONSTANT_Class alias rather than the
	// this_class CP slot. Cycle identity must be the resolved binary class name.
	self := setHierarchySuperToAliasedClass(t, classes["cycles/Solo"], "cycles/Solo")
	result, err := RunClasses([][]byte{self}, "cycles/Solo", "run", nil, hierarchyValidationGasLimit)
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 2, 0)

	parent := setHierarchySuperClass(t, classes["cycles/Parent"], "cycles/Child")
	bundle := [][]byte{classes["cycles/Child"], parent}
	result, err = RunClasses(bundle, "cycles/Child", "childRun", nil, hierarchyValidationGasLimit)
	// Child(0) -> Parent(1) -> Child(0): index 0 is the first repeated class.
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 2, 0)

	result, err = RunClasses(bundle, "cycles/Parent", "run", nil, hierarchyValidationGasLimit)
	// Starting at Parent reverses which node is repeated first.
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 2, 1)
}

func TestM3dHierarchyClassAliasResolvesARealParent(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"alias/Parent.java": `package alias; public class Parent { static int value = 12; }`,
		"alias/Child.java": `package alias; public final class Child extends Parent {
			public static int run() { return value; }
		}`,
	}, "alias/Parent", "alias/Child")
	child := setHierarchySuperToAliasedClass(t, classes["alias/Child"], "alias/Parent")
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{child, classes["alias/Parent"]}, "alias/Child", "run", nil,
			hierarchyValidationGasLimit,
		)
	}, 12)
}

func TestM3dHierarchyError3FinalParentReportsOffendingChild(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"finalparent/Parent.java": `package finalparent; public class Parent { }`,
		"finalparent/Child.java": `package finalparent; public class Child extends Parent {
			public static int run() { return 1; }
		}`,
	}, "finalparent/Parent", "finalparent/Child")
	parent := mutateHierarchyClass(t, classes["finalparent/Parent"], func(out []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(out[c.cpEnd:])
		binary.BigEndian.PutUint16(out[c.cpEnd:], flags|0x0010)
	})
	result, err := RunClasses(
		[][]byte{parent, classes["finalparent/Child"]}, "finalparent/Child", "run", nil,
		hierarchyValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 3, 1)
}

func TestM3dHierarchyError4InvalidKindsAndZeroSuperRules(t *testing.T) {
	t.Run("interface-used-as-superclass", func(t *testing.T) {
		classes := compileBundleValidationJava(t, map[string]string{
			"badkind/Parent.java": `package badkind; public class Parent { }`,
			"badkind/Face.java":   `package badkind; public interface Face { static int marker() { return 1; } }`,
			"badkind/Child.java": `package badkind; public class Child extends Parent {
				static int mention() { return Face.marker(); }
				public static int run() { return 2; }
			}`,
		}, "badkind/Face", "badkind/Child")
		child := setHierarchySuperClass(t, classes["badkind/Child"], "badkind/Face")
		result, err := RunClasses(
			[][]byte{classes["badkind/Face"], child}, "badkind/Child", "run", nil,
			hierarchyValidationGasLimit,
		)
		assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 4, 1)
	})

	t.Run("ordinary-class-has-zero-super", func(t *testing.T) {
		classfile := compileJava(t, "ZeroSuperChild", `public class ZeroSuperChild {
			public static int run() { return 3; }
		}`)
		classfile = mutateHierarchyClass(t, classfile, func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(out[c.cpEnd+4:], 0)
		})
		result, err := RunClasses(
			[][]byte{classfile}, "ZeroSuperChild", "run", nil, hierarchyValidationGasLimit,
		)
		assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 4, 0)
	})

	t.Run("Object-has-nonzero-super", func(t *testing.T) {
		classes := compileBundleValidationJava(t, map[string]string{
			"objectparent/Parent.java": `package objectparent; public class Parent { public static int value; }`,
			"java/lang/Object.java": `package java.lang; public class Object {
				static int mention() { return objectparent.Parent.value; }
				public static int run() { return 4; }
			}`,
		}, "objectparent/Parent", "java/lang/Object")
		objectClass := setHierarchySuperClass(t, classes["java/lang/Object"], "objectparent/Parent")
		result, err := RunClasses(
			[][]byte{classes["objectparent/Parent"], objectClass},
			"java/lang/Object", "run", nil, hierarchyValidationGasLimit,
		)
		assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 4, 1)
	})
}

func TestM3dHierarchyError5InaccessibleParentReportsChild(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"parentpkg/Parent.java": `package parentpkg; public class Parent { }`,
		"childpkg/Child.java": `package childpkg; public class Child extends parentpkg.Parent {
			public static int run() { return 5; }
		}`,
	}, "parentpkg/Parent", "childpkg/Child")
	parent := mutateHierarchyClass(t, classes["parentpkg/Parent"], func(out []byte, c staticsClass) {
		flags := binary.BigEndian.Uint16(out[c.cpEnd:])
		binary.BigEndian.PutUint16(out[c.cpEnd:], flags&^uint16(0x0001))
	})
	result, err := RunClasses(
		[][]byte{parent, classes["childpkg/Child"]}, "childpkg/Child", "run", nil,
		hierarchyValidationGasLimit,
	)
	assertBundleValidationError(t, result, err, "HierarchyError(uint256,uint256)", 5, 1)
}

func TestM3dMalformedSuperclassCPRetainsExactClassError(t *testing.T) {
	original := compileJava(t, "MalformedSuper", `public class MalformedSuper {
		public static int run() { return 1; }
	}`)
	parsed := parseStaticsClass(t, original)
	cases := map[string]func([]byte, staticsClass){
		"super-index-out-of-range": func(out []byte, c staticsClass) {
			binary.BigEndian.PutUint16(out[c.cpEnd+4:], uint16(c.cpCount))
		},
		"super-entry-wrong-tag": func(out []byte, c staticsClass) {
			// super_class must designate CONSTANT_Class, never a raw Utf8 entry.
			binary.BigEndian.PutUint16(out[c.cpEnd+4:], c.utfIndex(t, "MalformedSuper"))
		},
		"super-class-name-index-zero": func(out []byte, c staticsClass) {
			super := binary.BigEndian.Uint16(out[c.cpEnd+4:])
			binary.BigEndian.PutUint16(out[c.entry(t, super).offset+1:], 0)
		},
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			bad := mutateHierarchyClass(t, original, mutate)
			result, err := RunClasses([][]byte{bad}, "MalformedSuper", "run", nil, hierarchyValidationGasLimit)
			assertBundleValidationError(
				t, result, err, "ClassError(uint256,uint256)", 10, uint64(parsed.cpEnd+6),
			)
		})
	}
}

func TestM3dInheritedHiddenOverloadedMembersAndSiblingStorage(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"members/Parent.java": `package members; public class Parent {
			public static int shared = 1;
			public static int hidden = 2;
			public static int pick(int x) { return x + 10; }
			public static int pick(int x, int y) { return x * 10 + y; }
		}`,
		"members/Child.java": `package members; public class Child extends Parent {
			public static int hidden = 3;
			public static int pick(int x) { return x + 20; }
		}`,
		"members/Sibling.java": `package members; public class Sibling extends Parent { }`,
		"members/Driver.java": `package members; public final class Driver {
			public static int run(int x) {
				Child.shared = x;
				return Child.shared * 100000 + Sibling.shared * 10000
					+ Parent.hidden * 1000 + Child.hidden * 100
					+ Child.pick(x) * 10 + Child.pick(x, 4);
			}
		}`,
	}, "members/Parent", "members/Child", "members/Sibling", "members/Driver")
	driver := mutateHierarchyClass(t, classes["members/Driver"], func(out []byte, c staticsClass) {
		redirectHierarchyFieldOwner(t, out, c, "run", "shared", opPutstatic, "members/Child")
		redirectHierarchyFieldOwner(t, out, c, "run", "shared", opGetstatic, "members/Child")
		redirectHierarchyFieldOwnerOccurrence(t, out, c, "run", "shared", opGetstatic, "members/Sibling", 1)
		redirectHierarchyCallOwner(t, out, c, "run", "pick", "(II)I", "members/Child")
	})
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["members/Sibling"], driver, classes["members/Parent"], classes["members/Child"]},
			"members/Driver", "run", []int32{2}, hierarchyValidationGasLimit,
		)
	}, 222544)
}

func TestM3dFirstHiddenDeclarationWinsBeforeAccessChecks(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"shadow/Parent.java": `package shadow; public class Parent {
			public static int field = 1;
			public static int method() { return 2; }
		}`,
		"shadow/Child.java": `package shadow; public class Child extends Parent {
			public static int field = 3;
			public static int method() { return 4; }
		}`,
		"shadowcaller/Driver.java": `package shadowcaller; public final class Driver {
			public static int read() { return shadow.Child.field; }
			public static int call() { return shadow.Child.method(); }
		}`,
	}, "shadow/Parent", "shadow/Child", "shadowcaller/Driver")
	child := mutateHierarchyClass(t, classes["shadow/Child"], func(out []byte, c staticsClass) {
		field := c.field(t, "field", "I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], (field.access&^accessMask)|accPrivate|accStatic)
		method := c.method(t, "method", "()I")
		binary.BigEndian.PutUint16(out[method.accessOffset:], (method.access&^accessMask)|accPrivate|accStatic)
	})
	driver := classes["shadowcaller/Driver"]
	_, fieldPC := parseStaticsClass(t, driver).fieldInstruction(t, "read", opGetstatic, 0)
	_, callPC := parseCallValidationClass(t, driver).callRef(t, "call")
	bundle := [][]byte{classes["shadow/Parent"], driver, child}
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "shadowcaller/Driver", "read", nil, hierarchyValidationGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(fieldPC))
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "shadowcaller/Driver", "call", nil, hierarchyValidationGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(callPC))
}

func TestM3dPublicSymbolicChildDoesNotRecheckHiddenDeclaringClass(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"hidden/Parent.java": `package hidden; class Parent {
			public static int field = 6;
			public static int value() { return 7; }
		}`,
		"hidden/Child.java": `package hidden; public class Child extends Parent { }`,
		"outside/Driver.java": `package outside; public final class Driver {
			public static int run() { return hidden.Child.field * 10 + hidden.Child.value(); }
		}`,
	}, "hidden/Parent", "hidden/Child", "outside/Driver")
	driver := mutateHierarchyClass(t, classes["outside/Driver"], func(out []byte, c staticsClass) {
		redirectHierarchyFieldOwner(t, out, c, "run", "field", opGetstatic, "hidden/Child")
		redirectHierarchyCallOwner(t, out, c, "run", "value", "()I", "hidden/Child")
	})
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["hidden/Parent"], driver, classes["hidden/Child"]},
			"outside/Driver", "run", nil, hierarchyValidationGasLimit,
		)
	}, 67)
}

func TestM3dProtectedStaticsAllowSubclassAndRejectUnrelatedCallerExactly(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"protectedbase/Parent.java": `package protectedbase; public class Parent {
			public static int field = 4;
			public static int method() { return 5; }
		}`,
		"protectedsub/Child.java": `package protectedsub; public class Child extends protectedbase.Parent {
			public static int run() { return Child.field * 10 + Child.method(); }
		}`,
		"protectedother/Caller.java": `package protectedother; public final class Caller {
			public static int field() { return protectedsub.Child.field; }
			public static int call() { return protectedsub.Child.method(); }
		}`,
	}, "protectedbase/Parent", "protectedsub/Child", "protectedother/Caller")
	parent := mutateHierarchyClass(t, classes["protectedbase/Parent"], func(out []byte, c staticsClass) {
		field := c.field(t, "field", "I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], (field.access&^accessMask)|0x0004|accStatic)
		method := c.method(t, "method", "()I")
		binary.BigEndian.PutUint16(out[method.accessOffset:], (method.access&^accessMask)|0x0004|accStatic)
	})
	child := mutateHierarchyClass(t, classes["protectedsub/Child"], func(out []byte, c staticsClass) {
		redirectHierarchyFieldOwner(t, out, c, "run", "field", opGetstatic, "protectedsub/Child")
		redirectHierarchyCallOwner(t, out, c, "run", "method", "()I", "protectedsub/Child")
	})
	caller := mutateHierarchyClass(t, classes["protectedother/Caller"], func(out []byte, c staticsClass) {
		redirectHierarchyFieldOwner(t, out, c, "field", "field", opGetstatic, "protectedsub/Child")
		redirectHierarchyCallOwner(t, out, c, "call", "method", "()I", "protectedsub/Child")
	})
	bundle := [][]byte{caller, classes["protectedsub/Child"], parent}
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses([][]byte{parent, child}, "protectedsub/Child", "run", nil, hierarchyValidationGasLimit)
	}, 45)

	_, fieldPC := parseStaticsClass(t, caller).fieldInstruction(t, "field", opGetstatic, 0)
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "protectedother/Caller", "field", nil, hierarchyValidationGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(fieldPC))
	_, callPC := parseCallValidationClass(t, caller).callRef(t, "call")
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "protectedother/Caller", "call", nil, hierarchyValidationGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(callPC))
}

func TestM3dResolvedParentFrameKeepsPrivateDeclaringClassContext(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"privatecontext/Parent.java": `package privatecontext; public class Parent {
			private static int secret = 8;
			private static int helper() { return secret + 1; }
			public static int directField = 2;
			public static int directMethod() { return 3; }
			public static int expose() { return secret * 10 + helper(); }
		}`,
		"privatecontext/Child.java": `package privatecontext; public class Child extends Parent { }`,
		"privatecontext/Driver.java": `package privatecontext; public final class Driver {
			public static int run() { return Child.expose(); }
			public static int readPrivate() { return Child.directField; }
			public static int callPrivate() { return Child.directMethod(); }
		}`,
	}, "privatecontext/Parent", "privatecontext/Child", "privatecontext/Driver")
	parent := mutateHierarchyClass(t, classes["privatecontext/Parent"], func(out []byte, c staticsClass) {
		field := c.field(t, "directField", "I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], (field.access&^accessMask)|accPrivate|accStatic)
		method := c.method(t, "directMethod", "()I")
		binary.BigEndian.PutUint16(out[method.accessOffset:], (method.access&^accessMask)|accPrivate|accStatic)
	})
	driver := mutateHierarchyClass(t, classes["privatecontext/Driver"], func(out []byte, c staticsClass) {
		redirectHierarchyCallOwner(t, out, c, "run", "expose", "()I", "privatecontext/Child")
		redirectHierarchyFieldOwner(t, out, c, "readPrivate", "directField", opGetstatic, "privatecontext/Child")
		redirectHierarchyCallOwner(t, out, c, "callPrivate", "directMethod", "()I", "privatecontext/Child")
	})
	bundle := [][]byte{classes["privatecontext/Child"], driver, parent}
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(bundle, "privatecontext/Driver", "run", nil, hierarchyValidationGasLimit)
	}, 89)

	_, fieldPC := parseStaticsClass(t, driver).fieldInstruction(t, "readPrivate", opGetstatic, 0)
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "privatecontext/Driver", "readPrivate", nil, hierarchyValidationGasLimit)
	}, "FieldError(uint256,uint256)", 4, uint64(fieldPC))
	_, callPC := parseCallValidationClass(t, driver).callRef(t, "callPrivate")
	assertStaticsError(t, func() (Result, error) {
		return RunClasses(bundle, "privatecontext/Driver", "callPrivate", nil, hierarchyValidationGasLimit)
	}, "CallError(uint256,uint256)", 4, uint64(callPC))
}

func TestM3dSuperclassInitializationOrderAndNoClinitChild(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"initorder/Parent.java": `package initorder; public class Parent {
			static int value = initialize();
			static int initialize() { NoClinitChild.touched = 7; return 3; }
		}`,
		"initorder/NoClinitChild.java": `package initorder; public class NoClinitChild extends Parent {
			static int touched;
			public static int run() { return value * 10 + touched; }
		}`,
		"initorder/OrderedChild.java": `package initorder; public class OrderedChild extends Parent {
			static int child = value + 4;
			public static int run() { return value * 10 + child; }
		}`,
	}, "initorder/Parent", "initorder/NoClinitChild", "initorder/OrderedChild")
	for _, method := range parseStaticsClass(t, classes["initorder/NoClinitChild"]).methods {
		if method.name == "<clinit>" {
			t.Fatal("NoClinitChild unexpectedly contains <clinit>")
		}
	}
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["initorder/NoClinitChild"], classes["initorder/Parent"]},
			"initorder/NoClinitChild", "run", nil, hierarchyValidationGasLimit,
		)
	}, 37)
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["initorder/OrderedChild"], classes["initorder/Parent"], classes["initorder/NoClinitChild"]},
			"initorder/OrderedChild", "run", nil, hierarchyValidationGasLimit,
		)
	}, 37)
}

func TestM3dInheritedActiveUseInitializesDeclaringOwnerOnly(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"ownerinit/Parent.java": `package ownerinit; public class Parent {
			public static int side;
			public static int value = 3;
		}`,
		"ownerinit/Child.java": `package ownerinit; public class Child extends Parent {
			static int marker = mark();
			static int mark() { Parent.side = 9; return 1; }
		}`,
		"ownerinit/Driver.java": `package ownerinit; public final class Driver {
			public static int run() { return Child.value * 10 + Parent.side; }
		}`,
	}, "ownerinit/Parent", "ownerinit/Child", "ownerinit/Driver")
	driver := mutateHierarchyClass(t, classes["ownerinit/Driver"], func(out []byte, c staticsClass) {
		redirectHierarchyFieldOwner(t, out, c, "run", "value", opGetstatic, "ownerinit/Child")
	})
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["ownerinit/Child"], driver, classes["ownerinit/Parent"]},
			"ownerinit/Driver", "run", nil, hierarchyValidationGasLimit,
		)
	}, 30)
}

func TestM3dChildConstantPreparedBeforeReentrantParentInitialization(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"reentrant/Parent.java": `package reentrant; public class Parent {
			static int CONST;
			static int seenConstant = Child.probe;
			static int seenCall = Child.before();
		}`,
		"reentrant/Child.java": `package reentrant; public class Child extends Parent {
			public static final int CONST = 7;
			static int probe = 4;
			public static int before() { return CONST + probe; }
			public static int run() { return seenConstant * 100 + seenCall * 10 + probe; }
		}`,
	}, "reentrant/Parent", "reentrant/Child")
	parent := mutateHierarchyClass(t, classes["reentrant/Parent"], func(out []byte, c staticsClass) {
		// javac would inline Child.CONST. Redirect the valid Child.probe Fieldref to
		// the existing CONST:I name-and-type so this is an actual getstatic while
		// Child is marked initializing but before Parent and Child <clinit> run.
		redirectHierarchyFieldName(t, out, c, "<clinit>", "probe", "CONST")
	})
	assertHierarchyValue(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["reentrant/Child"], parent}, "reentrant/Child", "run", nil,
			hierarchyValidationGasLimit,
		)
	}, 774)
}

func TestM3dInheritedFinalWritesUseActualDeclaringOwnerAndClinitContext(t *testing.T) {
	t.Run("declaring-parent-clinit-may-write", func(t *testing.T) {
		classes := compileBundleValidationJava(t, map[string]string{
			"finalwrite/Parent.java": `package finalwrite; public class Parent {
				public static int value;
				static { value = 8; }
			}`,
			"finalwrite/Child.java": `package finalwrite; public class Child extends Parent {
				public static int run() { return Child.value; }
			}`,
		}, "finalwrite/Parent", "finalwrite/Child")
		parent := setHierarchyFieldFinal(t, classes["finalwrite/Parent"], "value")
		assertHierarchyValue(t, func() (Result, error) {
			return RunClasses(
				[][]byte{classes["finalwrite/Child"], parent}, "finalwrite/Child", "run", nil,
				hierarchyValidationGasLimit,
			)
		}, 8)
	})

	t.Run("child-clinit-may-not-write-parent-final", func(t *testing.T) {
		classes := compileBundleValidationJava(t, map[string]string{
			"badfinal/Parent.java": `package badfinal; public class Parent { public static int value; }`,
			"badfinal/Child.java": `package badfinal; public class Child extends Parent {
				static { Parent.value = 7; }
				public static int run() { return value; }
			}`,
		}, "badfinal/Parent", "badfinal/Child")
		parent := setHierarchyFieldFinal(t, classes["badfinal/Parent"], "value")
		_, putPC := parseStaticsClass(t, classes["badfinal/Child"]).fieldInstruction(t, "<clinit>", opPutstatic, 0)
		assertStaticsError(t, func() (Result, error) {
			return RunClasses(
				[][]byte{parent, classes["badfinal/Child"]}, "badfinal/Child", "run", nil,
				hierarchyValidationGasLimit,
			)
		}, "FieldError(uint256,uint256)", 4, uint64(putPC))
	})
}

func TestM3dParentInitializerOutcomesAndOOGStayDistinct(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"parentoutcome/FailParent.java": `package parentoutcome; public class FailParent {
			static int value = 9 / zero();
			static int zero() { return 0; }
			public static int divide(int x) { return 9 / x; }
		}`,
		"parentoutcome/FailChild.java": `package parentoutcome; public class FailChild extends FailParent {
			static int marker = Missing.value();
			public static int run() { return marker; }
		}`,
		"parentoutcome/Missing.java": `package parentoutcome; public final class Missing {
			public static int value() { return 1; }
		}`,
		"parentoutcome/OutsideParent.java": `package parentoutcome; public class OutsideParent {
			public static int divide(int x) { return 9 / x; }
		}`,
		"parentoutcome/OutsideChild.java": `package parentoutcome; public class OutsideChild extends OutsideParent {
			public static int run(int x) { return divide(x); }
		}`,
		"parentoutcome/OverflowParent.java": `package parentoutcome; public class OverflowParent {
			static int value = recurse();
			static int recurse() { return recurse(); }
		}`,
		"parentoutcome/OverflowChild.java": `package parentoutcome; public class OverflowChild extends OverflowParent {
			public static int run() { return value; }
		}`,
	}, "parentoutcome/FailParent", "parentoutcome/FailChild", "parentoutcome/OutsideParent",
		"parentoutcome/OutsideChild", "parentoutcome/OverflowParent", "parentoutcome/OverflowChild")
	failBundle := [][]byte{classes["parentoutcome/FailChild"], classes["parentoutcome/FailParent"]}
	// Parent arithmetic wins before the child's omitted symbolic owner can be
	// resolved, proving the child initializer did not execute after parent failure.
	assertStaticsException(t, func() (Result, error) {
		return RunClasses(failBundle, "parentoutcome/FailChild", "run", nil, hierarchyValidationGasLimit)
	}, "java.lang.ExceptionInInitializerError")
	assertStaticsException(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["parentoutcome/OutsideChild"], classes["parentoutcome/OutsideParent"]},
			"parentoutcome/OutsideChild", "run", []int32{0}, hierarchyValidationGasLimit,
		)
	}, "java.lang.ArithmeticException")
	assertStaticsException(t, func() (Result, error) {
		return RunClasses(
			[][]byte{classes["parentoutcome/OverflowParent"], classes["parentoutcome/OverflowChild"]},
			"parentoutcome/OverflowChild", "run", nil, hierarchyValidationGasLimit,
		)
	}, "java.lang.StackOverflowError")

	result, err := RunClasses(failBundle, "parentoutcome/FailChild", "run", nil, 1)
	if err == nil || !errors.Is(err, vm.ErrOutOfGas) {
		t.Fatalf("result/error = %+v/%v, want true EVM out of gas", result, err)
	}
	if result.ExceptionClass != "" || len(result.RevertData) != 0 {
		t.Fatalf("out of gas was mislabeled as an initializer outcome: %+v", result)
	}
}

func TestM3dRootEntryRemainsDeclaredMethodOnly(t *testing.T) {
	classes := compileBundleValidationJava(t, map[string]string{
		"entrydecl/Parent.java": `package entrydecl; public class Parent {
			public static int run() { return 9; }
		}`,
		"entrydecl/Child.java": `package entrydecl; public class Child extends Parent { }`,
	}, "entrydecl/Parent", "entrydecl/Child")
	result, err := RunClasses(
		[][]byte{classes["entrydecl/Parent"], classes["entrydecl/Child"]},
		"entrydecl/Child", "run", nil, hierarchyValidationGasLimit,
	)
	assertHierarchyMethodError(t, result, err, 1)
}

func assertHierarchyValue(t *testing.T, run func() (Result, error), want int32) {
	t.Helper()
	result, err := run()
	if err != nil {
		t.Fatalf("EVM execution failed: %v (result=%+v)", err, result)
	}
	if result.ExceptionClass != "" || result.Value != want || result.GasUsed == 0 || len(result.RevertData) != 0 {
		t.Fatalf("result = %+v, want exact successful value %d", result, want)
	}
}

func assertHierarchyMethodError(t *testing.T, result Result, err error, code uint64) {
	t.Helper()
	if err == nil || !strings.Contains(err.Error(), "execution reverted") {
		t.Fatalf("result/error = %+v/%v, want exact MethodError revert", result, err)
	}
	selector := crypto.Keccak256([]byte("MethodError(uint256)"))[:4]
	if result.ExceptionClass != "" || result.GasUsed == 0 || len(result.RevertData) != 36 || !bytes.Equal(result.RevertData[:4], selector) {
		t.Fatalf("result = %+v, want exact MethodError payload", result)
	}
	if !bytes.Equal(result.RevertData[4:28], make([]byte, 24)) || binary.BigEndian.Uint64(result.RevertData[28:]) != code {
		t.Fatalf("MethodError payload = %x, want code %d", result.RevertData, code)
	}
}

func compileHierarchyValidationJava(t *testing.T, sources map[string]string) (map[string][]byte, string) {
	t.Helper()
	dir := t.TempDir()
	paths := make([]string, 0, len(sources))
	for relative, source := range sources {
		path := filepath.Join(dir, filepath.FromSlash(relative))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(source), 0o600); err != nil {
			t.Fatal(err)
		}
		paths = append(paths, path)
	}
	sort.Strings(paths)
	args := append([]string{"--release", "8", "-d", dir}, paths...)
	if output, err := exec.Command("javac", args...).CombinedOutput(); err != nil {
		t.Fatalf("javac failed: %v\n%s", err, output)
	}
	classes := make(map[string][]byte)
	if err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || filepath.Ext(path) != ".class" {
			return nil
		}
		relative, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		name := strings.TrimSuffix(filepath.ToSlash(relative), ".class")
		classes[name] = data
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	return classes, dir
}

func mutateHierarchyClass(t *testing.T, original []byte, mutate func([]byte, staticsClass)) []byte {
	t.Helper()
	out := append([]byte(nil), original...)
	mutate(out, parseStaticsClass(t, out))
	return out
}

func hierarchyClassIndex(t *testing.T, c staticsClass, name string) uint16 {
	t.Helper()
	for index := 1; index < len(c.entries); index++ {
		entry := c.entries[index]
		if entry.tag == 7 && c.utf8[c.u2(t, entry.offset+1)] == name {
			return uint16(index)
		}
	}
	t.Fatalf("test Class constant %q not found", name)
	return 0
}

func setHierarchySuperClass(t *testing.T, original []byte, name string) []byte {
	t.Helper()
	return mutateHierarchyClass(t, original, func(out []byte, c staticsClass) {
		binary.BigEndian.PutUint16(out[c.cpEnd+4:], hierarchyClassIndex(t, c, name))
	})
}

func setHierarchySuperToAliasedClass(t *testing.T, original []byte, name string) []byte {
	t.Helper()
	c := parseStaticsClass(t, original)
	classIndex := hierarchyClassIndex(t, c, name)
	nameIndex := c.u2(t, c.entry(t, classIndex).offset+1)
	if c.cpCount >= 65535 {
		t.Fatal("test constant pool is full")
	}
	out := make([]byte, len(original)+3)
	copy(out, original[:c.cpEnd])
	out[c.cpEnd] = 7
	binary.BigEndian.PutUint16(out[c.cpEnd+1:], nameIndex)
	copy(out[c.cpEnd+3:], original[c.cpEnd:])
	binary.BigEndian.PutUint16(out[8:10], uint16(c.cpCount+1))
	// The header moved by three bytes when the alias was inserted at old cpEnd.
	binary.BigEndian.PutUint16(out[c.cpEnd+3+4:], uint16(c.cpCount))
	return out
}

func hierarchyRefNameDescriptor(t *testing.T, c staticsClass, index uint16) (string, string) {
	t.Helper()
	entry := c.entry(t, index)
	if entry.tag != 9 && entry.tag != 10 {
		t.Fatalf("CP #%d tag = %d, want field or method ref", index, entry.tag)
	}
	nat := c.entry(t, c.u2(t, entry.offset+3))
	if nat.tag != 12 {
		t.Fatalf("CP #%d name-and-type tag = %d", index, nat.tag)
	}
	return c.utf8[c.u2(t, nat.offset+1)], c.utf8[c.u2(t, nat.offset+3)]
}

func redirectHierarchyFieldOwner(t *testing.T, out []byte, c staticsClass, method, field string, opcode byte, owner string) {
	t.Helper()
	redirectHierarchyFieldOwnerOccurrence(t, out, c, method, field, opcode, owner, 0)
}

func redirectHierarchyFieldOwnerOccurrence(t *testing.T, out []byte, c staticsClass, method, field string, opcode byte, owner string, occurrence int) {
	t.Helper()
	code := c.namedMethod(t, method).code
	seen := 0
	for pc := 0; pc+2 < len(code); pc++ {
		if code[pc] != opcode {
			continue
		}
		ref := binary.BigEndian.Uint16(code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 9 {
			continue
		}
		name, _ := hierarchyRefNameDescriptor(t, c, ref)
		if name != field {
			continue
		}
		if seen == occurrence {
			binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], hierarchyClassIndex(t, c, owner))
			return
		}
		seen++
	}
	t.Fatalf("method %s has no %dth %s field opcode 0x%02x: %x", method, occurrence, field, opcode, code)
}

func redirectHierarchyCallOwner(t *testing.T, out []byte, c staticsClass, method, name, descriptor, owner string) {
	t.Helper()
	code := c.namedMethod(t, method).code
	for pc := 0; pc+2 < len(code); pc++ {
		if code[pc] != 0xb8 {
			continue
		}
		ref := binary.BigEndian.Uint16(code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 10 {
			continue
		}
		refName, refDescriptor := hierarchyRefNameDescriptor(t, c, ref)
		if refName == name && refDescriptor == descriptor {
			binary.BigEndian.PutUint16(out[c.entry(t, ref).offset+1:], hierarchyClassIndex(t, c, owner))
			return
		}
	}
	t.Fatalf("method %s has no invokestatic %s%s: %x", method, name, descriptor, code)
}

func redirectHierarchyFieldName(t *testing.T, out []byte, c staticsClass, method, from, to string) {
	t.Helper()
	code := c.namedMethod(t, method).code
	for pc := 0; pc+2 < len(code); pc++ {
		if code[pc] != opGetstatic {
			continue
		}
		ref := binary.BigEndian.Uint16(code[pc+1:])
		if ref == 0 || int(ref) >= len(c.entries) || c.entries[ref].tag != 9 {
			continue
		}
		name, descriptor := hierarchyRefNameDescriptor(t, c, ref)
		if name == from && descriptor == "I" {
			nat := c.entry(t, c.u2(t, c.entry(t, ref).offset+3))
			binary.BigEndian.PutUint16(out[nat.offset+1:], c.utfIndex(t, to))
			return
		}
	}
	t.Fatalf("method %s has no getstatic %s:I: %x", method, from, code)
}

func setHierarchyFieldFinal(t *testing.T, original []byte, name string) []byte {
	t.Helper()
	return mutateHierarchyClass(t, original, func(out []byte, c staticsClass) {
		field := c.field(t, name, "I")
		binary.BigEndian.PutUint16(out[field.accessOffset:], field.access|accFinal)
	})
}
