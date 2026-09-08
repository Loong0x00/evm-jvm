// Copyright 2026 The go-ethereum Authors
// This file is part of the go-ethereum library.

package jvmevm

import (
	"fmt"
	"testing"
)

// An interface may already be erroneous before a NEW implementing class is
// actively used. Skipping that prerequisite must not initialize the new class.
func TestParentM5daPreviouslyFailedDefaultPrerequisite(t *testing.T) {
	classes := compileJavaSources(t, map[string]string{
		"ParentFailedDefault.java": `public class ParentFailedDefault {
			static int zero, entered;
			public static int run(int mode) {
				try { if(mode<4){int ignored=ParentBadDefault.N;}else{new ParentEarlierImplementor();} }
				catch(ExceptionInInitializerError expected) {}
				try { switch(mode&3) {
					case 0: return new ParentLaterImplementor().value();
					case 1: return ParentLaterImplementor.own;
					case 2: ParentLaterImplementor.own=9; return -2;
					default: return ParentLaterImplementor.read();
				} } catch(NoClassDefFoundError expected) {
					try{ParentLaterImplementor.read();return -5;}
					catch(NoClassDefFoundError again){return 88+100*entered;}
				}
			}
		}`,
		"ParentBadDefault.java": `public interface ParentBadDefault {
			int N=1/ParentFailedDefault.zero; default int value(){return 2;}
		}`,
		"ParentEarlierImplementor.java": `public class ParentEarlierImplementor implements ParentBadDefault {}`,
		"ParentLaterImplementor.java": `public class ParentLaterImplementor implements ParentBadDefault {
			static int own=initialize(); static int read(){return own;}
			static int initialize(){ParentFailedDefault.entered++;return 7;}
		}`,
	})
	bundle := [][]byte{classes["ParentFailedDefault"], classes["ParentBadDefault"], classes["ParentLaterImplementor"], classes["ParentEarlierImplementor"]}
	for mode := int32(0); mode < 8; mode++ {
		t.Run(fmt.Sprintf("active-use-%d", mode), func(t *testing.T) {
			verifyM5cdJava8Outcome(t, bundle, "ParentFailedDefault", "run", []int32{mode}, "value=88")
			result, err := RunClasses(bundle, "ParentFailedDefault", "run", []int32{mode}, 80_000_000)
			if err != nil || result.ExceptionClass != "" || result.Value != 88 {
				t.Fatalf("result/error=%+v/%v want value=88", result, err)
			}
		})
	}
}
