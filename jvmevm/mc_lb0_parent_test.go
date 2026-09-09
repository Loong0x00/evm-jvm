package jvmevm

import (
	"context"
	"crypto/sha256"
	"fmt"
	"math/rand"
	"os/exec"
	"strconv"
	"strings"
	"testing"
	"time"
)

// Parent-owned synthetic Object layout probes. These exercise the explicit EVM
// heap quota policy, NOT a host JVM with replaced platform classes.
func TestMCLB0ParentStringInheritedFieldLimit(t *testing.T) {
	for _, n := range []int{0, 1, 1022, 1023} {
		mcLB0VerifyBoundaryWatchdog(t, fmt.Sprintf("parent-inherited-%d", n), 120*time.Second, func(t *testing.T) {
			var object strings.Builder
			object.WriteString("package java.lang; public class Object {public Object(){}")
			for i := 0; i < n; i++ {
				fmt.Fprintf(&object, "public int f%d;", i)
			}
			object.WriteString("}")
			root := `public class ParentStringFields {public static int run(){try{return "A".length();}catch(OutOfMemoryError e){Object o=new Object();try{return "B".length();}catch(OutOfMemoryError second){return o==null?0:7;}}}}`
			c := mcLB0VerifyCompile(t, map[string]string{"java/lang/Object.java": object.String(), "ParentStringFields.java": root}, "java/lang/Object", "ParentStringFields")
			want := int32(1)
			if n == 1023 {
				want = 7
			}
			r := mcLB0VerifyAssertValue(t, func() (Result, error) {
				return RunClasses([][]byte{c.classes["java/lang/Object"], c.classes["ParentStringFields"]}, "ParentStringFields", "run", nil, 1_000_000_000)
			}, want)
			t.Logf("Object fields=%d String fields=%d value=%d gas=%d", n, n+2, r.Value, r.GasUsed)
		})
	}
}

func TestMCLB0ParentInheritedPreparationPoison(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "parent-inherited-preparation", 120*time.Second, func(t *testing.T) {
		var object strings.Builder
		object.WriteString("package java.lang;public class Object{public Object(){}")
		for i := 0; i < 1023; i++ {
			fmt.Fprintf(&object, "public int f%d;", i)
		}
		object.WriteString("}")
		c := mcLB0VerifyCompile(t, map[string]string{
			"java/lang/Object.java": object.String(),
			"ParentStringDep.java":  `public class ParentStringDep{static final String S="dep";public static int read(){return 1;}}`,
			"ParentStringPrep.java": `public class ParentStringPrep{public static int run(){int r=0;try{ParentStringDep.read();}catch(OutOfMemoryError e){r=7;}try{ParentStringDep.read();}catch(NoClassDefFoundError e){r+=12;}return r;}}`,
		}, "java/lang/Object", "ParentStringDep", "ParentStringPrep")
		r := mcLB0VerifyAssertValue(t, func() (Result, error) {
			return RunClasses([][]byte{c.classes["java/lang/Object"], c.classes["ParentStringDep"], c.classes["ParentStringPrep"]}, "ParentStringPrep", "run", nil, 1_000_000_000)
		}, 19)
		t.Logf("inherited String preparation OOM/NCDFE value%d gas%d", r.Value, r.GasUsed)
	})
}

func TestMCLB0ParentSeededUTF16CrossJVMVectors(t *testing.T) {
	mcLB0VerifyBoundaryWatchdog(t, "parent-utf16-vectors", 30*time.Second, func(t *testing.T) {
		rng := rand.New(rand.NewSource(0x4c4230))
		var source strings.Builder
		source.WriteString("public class ParentUTF16 {static String pick(int n){switch(n){")
		for i := 0; i < 96; i++ {
			var units []uint16
			switch i {
			case 0:
				units = []uint16{}
			case 1:
				units = []uint16{0}
			case 2:
				units = []uint16{'A', 'a'}
			case 3:
				units = []uint16{'B', 'B'}
			case 4:
				units = []uint16{0, 1, 0x7f, 0x80, 0x7ff, 0x800, 0xd7ff, 0xd800, 0xdbff, 0xdc00, 0xdfff, 0xffff}
			case 5:
				units = []uint16{0xd800, 0xdc00, 0xdbff, 0xdfff, 0xd800}
			default:
				for j := 0; j < 1+i%65; j++ {
					units = append(units, uint16(rng.Uint32()))
				}
			}
			fmt.Fprintf(&source, "case %d:return \"", i)
			for _, u := range units {
				if u < 256 {
					fmt.Fprintf(&source, "\\%03o", u)
				} else {
					fmt.Fprintf(&source, "\\u%04x", u)
				}
			}
			source.WriteString("\";")
		}
		source.WriteString(`default:return "";}}
 public static int probe(int i,int j,int k){String a=pick(i),b=pick(j);int h=a.hashCode();
 if(a.length()!=0)h=h*31+a.charAt((k&2147483647)%a.length());
 h=h*31+a.compareTo(b);h=h*31+(a.equals(b)?1:0);h=h*31+(a.intern()==a?1:0);
 h=h*31+(a.toString()==a?1:0);h=h*31+(a==pick(i)?1:0);
 CharSequence q=a;h=h*31+q.length();if(q.length()!=0)h=h*31+q.charAt(q.length()-1);
 Comparable<String> c=a;h=h*31+c.compareTo(b);
 Object[] refs=new Object[]{a,b};h=h*31+(a.equals(refs[0])?1:0);h=h*31+(a.equals(refs)?1:0);
 if((k&1)!=0){try{a.compareTo(null);h=0;}catch(NullPointerException e){h^=0x12345678;}}
 if((k&2)!=0){try{((Comparable)a).compareTo(new Object());h=0;}catch(ClassCastException e){h^=0x87654321;}}
 return h;}
 public static void main(String[] args){int[][] v=new int[][]{`)
		vectors := make([][3]int32, 192)
		for i := range vectors {
			vectors[i] = [3]int32{int32(i % 97), int32(rng.Intn(98)), int32(rng.Uint32())}
			v := vectors[i]
			fmt.Fprintf(&source, "{%d,%d,%d},", v[0], v[1], v[2])
		}
		source.WriteString("};for(int[] t:v)System.out.println(probe(t[0],t[1],t[2]));}}")
		compiled := mcLB0VerifyCompile(t, map[string]string{"ParentUTF16.java": source.String()}, "ParentUTF16")
		run := func(java string) []string {
			t.Helper()
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			out, err := exec.CommandContext(ctx, java, "-Xverify:all", "-Xmx64m", "-cp", compiled.dir, "ParentUTF16").CombinedOutput()
			if err != nil {
				t.Fatalf("%s %v %s", java, err, out)
			}
			return strings.Fields(string(out))
		}
		j8, j21 := run("/usr/lib/jvm/java-8-openjdk/bin/java"), run("java")
		if len(j8) != len(vectors) || len(j21) != len(vectors) {
			t.Fatalf("oracle lengths %d/%d", len(j8), len(j21))
		}
		var maxGas uint64
		for i, v := range vectors {
			if j8[i] != j21[i] {
				t.Fatalf("JVM discrepancy vector%d", i)
			}
			want, err := strconv.ParseInt(j8[i], 10, 32)
			if err != nil {
				t.Fatal(err)
			}
			r := mcLB0VerifyAssertValue(t, func() (Result, error) {
				return Run(compiled.classes["ParentUTF16"], "probe", []int32{v[0], v[1], v[2]}, 100_000_000)
			}, int32(want))
			if r.GasUsed > maxGas {
				maxGas = r.GasUsed
			}
		}
		t.Logf("192 Java8/21/EVM vectors, 96 UTF16 literals, rawSHA256=%x maxGas=%d", sha256.Sum256(compiled.classes["ParentUTF16"]), maxGas)
	})
}
