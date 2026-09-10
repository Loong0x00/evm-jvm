package ioe0

import "testing"

func TestIOE0ParentInterfaceGettersRemainOrdinaryCode(t *testing.T) {
	src := `public class IPGet {interface G {String getMessage();Throwable getCause();}static class P extends java.io.IOException implements G{P(String m){super(m);}}public static int run(){String m=new String(new char[]{'i'});G p=new P(m);return p.getMessage()==m&&p.getCause()==null?1:0;}}`
	r, _ := ioe0VerifyFinal(t, src, "IPGet", "run", []string{"IPGet", "IPGet$G", "IPGet$P"}, 1, ioe0VerifyOrdinaryGas, 4096)
	ioe0VerifyRequireReturned(t, r, 1)
}

func TestIOE0ParentLargeInheritedWrapperLayout(t *testing.T) {
	src := `public class IPWrap {static class B{static int x=fail();static int fail(){int z=0;return 1/z;}}public static int run(){try{return B.x;}catch(ExceptionInInitializerError e){return e.getMessage()==null&&e.getException()!=null&&e.getCause()==e.getException()&&e.getCause().getCause()==null?1:0;}}}`
	cs := ioe0VerifyCompileTrusted(t, map[string]string{"IPWrap.java": src}, []string{"IPWrap", "IPWrap$B"})
	raw := append(ioe0VerifyRaw(cs, "IPWrap", "IPWrap$B"), ioe0VerifySyntheticObject(t, 1023, "canonical"))
	e := ioe0VerifyNewEnv(t)
	defer e.close()
	r := ioe0VerifyRunToEnd(t, e, "large-wrapper", raw, "IPWrap", "run", 4096, 4096, ioe0VerifyBoundaryGas, 65536)
	ioe0VerifyRequireReturned(t, r, 1)
	cp := r.snaps[len(r.snaps)-1]
	if cp.Machine.ExceptionObjects != 2 || cp.Machine.ExceptionFields != 3076 {
		t.Fatalf("large arena fields count %d/%d", cp.Machine.ExceptionObjects, cp.Machine.ExceptionFields)
	}
	found := false
	for _, h := range cp.Machine.Heap {
		if h.Object && h.Metadata.Uint64()&255 == 3 {
			if h.Count != 1026 {
				t.Fatal("wrapper uses ordinary field cap")
			}
			found = true
		}
	}
	if !found {
		t.Fatal("missing large VM wrapper")
	}
	ioe0VerifyValidateOK(t, e, raw, cp.Bytes)
}
