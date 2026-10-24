#!/usr/bin/env python3
"""Verify Java8 String image adds exactly ordinary valueOf(char) Code."""
import re, subprocess, sys

def disasm(path):
    text=subprocess.check_output(['javap','-p','-c',path],text=True)
    text=re.sub(r'\s+#\d+', '', text)
    text=re.sub(r'\s+#\d+\s+', ' ', text)
    text=re.sub(r'\s+', ' ', text)
    return text
old,new=map(disasm,sys.argv[1:3])
method='public static java.lang.String valueOf(char); Code: 0: iconst_1 1: newarray char 3: astore_1 4: aload_1 5: iconst_0 6: iload_0 7: castore 8: new // class java/lang/String 11: dup 12: aload_1 13: invokespecial // Method "<init>":([C)V 16: areturn'
assert method in new, 'ordinary char[] allocation/copy-constructor bytecode absent'
new_without=re.sub(r'public static java\.lang\.String valueOf\(char\); Code: .*? areturn', '', new, count=1)
new_without=re.sub(r'\s+', ' ', new_without).strip()
old=re.sub(r'\s+', ' ', old).strip()
assert new_without==old, 'pre-existing class structure or method disassembly changed'
print('PASS: javap class structure and every old method disassembly unchanged (CP indices normalized); only public static valueOf(char) ordinary Code appended')
