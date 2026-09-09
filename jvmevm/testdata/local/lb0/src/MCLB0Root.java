public final class MCLB0Root {
    static int side;
    static int mark(int v) { side = side * 10 + v; return v; }

    public static int emptyLength() { return "".length(); }
    public static int asciiLength() { return "Minecraft".length(); }
    public static int nulLength() { return "A\000B".length(); }
    public static int nulChar() { return "A\000B".charAt(1); }
    public static int asciiBoundaryChar() { return "\u007f".charAt(0); }
    public static int twoByteLowChar() { return "\u0080".charAt(0); }
    public static int twoByteHighChar() { return "\u07ff".charAt(0); }
    public static int threeByteLowChar() { return "\u0800".charAt(0); }
    public static int threeByteHighChar() { return "\uffff".charAt(0); }
    public static int pairLength() { return "\ud83d\ude00".length(); }
    public static int pairHighChar() { return "\ud83d\ude00".charAt(0); }
    public static int pairLowChar() { return "\ud83d\ude00".charAt(1); }
    public static int unpairedHighChar() { return "\ud800".charAt(0); }
    public static int unpairedLowChar() { return "\udc00".charAt(0); }
    public static int emptyTrue() { return "".isEmpty() ? 1 : 0; }
    public static int emptyFalse() { return "x".isEmpty() ? 1 : 0; }
    public static int indexedChar(int i) { return "q\000\u07ff\u0800z".charAt(i); }

    public static int emptyHash() { return "".hashCode(); }
    public static int asciiHash() { return "abc".hashCode(); }
    public static int nulHash() { return "a\000b".hashCode(); }
    public static int wrappedHash() { return "polygenelubricants".hashCode(); }
    public static int repeatedHash() { String s = "hash-cache"; return s.hashCode() ^ s.hashCode(); }
    public static int zeroHashRepeated() { String s = "f5a5a608"; return s.hashCode() | s.hashCode(); }

    public static int equalsSame() { return "same".equals("same") ? 1 : 0; }
    public static int equalsEqualContent() { String a = "equal-content"; String b = MCLB0Peer.equalContent(); return a.equals(b) ? 1 : 0; }
    public static int equalsDifferent() { return "left".equals("right") ? 1 : 0; }
    public static int equalsNull() { return "left".equals(null) ? 1 : 0; }
    public static int equalsNonString() { return "left".equals(new MCLB0Box(3)) ? 1 : 0; }
    public static int equalsUTF16() { return "\ud800\000\udc00".equals(MCLB0Peer.edgeContent()) ? 1 : 0; }

    public static int compareEqual() { return "abc".compareTo("abc"); }
    public static int compareFirstUnit() { return "abc".compareTo("xbc"); }
    public static int compareUnsignedUnit() { return "\uffff".compareTo("\000"); }
    public static int comparePrefixShort() { return "abc".compareTo("abcd"); }
    public static int comparePrefixLong() { return "abcd".compareTo("abc"); }
    public static int compareSurrogate() { return "\ud83d\ude00".compareTo("\ud83d\ude01"); }

    public static int toStringIdentity() { String s = "self"; return s.toString() == s ? 1 : 0; }
    public static int internIdentity() { String s = "interned"; return s.intern() == s ? 1 : 0; }
    public static int cpHitIdentity() { return "cp-hit" == "cp-hit" ? 1 : 0; }
    public static int cpHitAfterCalls() { String a = "repeat"; int n = a.length(); String b = "repeat"; return (a == b ? 100 : 0) + n; }
    public static int crossClassIdentity() { return "cross-shared" == MCLB0Peer.shared() ? 1 : 0; }
    public static int crossFieldIdentity() { return "cross-field" == MCLB0Peer.SHARED ? 1 : 0; }

    public static int staticNonfinalLength() { return MCLB0Statics.NONFINAL.length(); }
    public static int staticNonfinalIdentity() { return MCLB0Statics.NONFINAL == "nonfinal" ? 1 : 0; }
    public static int clinitStringLength() { return MCLB0Statics.FROM_CLINIT.length(); }
    public static int clinitOrder() { return MCLB0Statics.STEP; }
    public static int clinitSharedIdentity() { return MCLB0Statics.FROM_CLINIT == MCLB0Peer.clinitValue() ? 1 : 0; }

    public static int charSequenceLength() { CharSequence s = "sequence"; return s.length(); }
    public static int charSequenceChar() { CharSequence s = "sequence"; return s.charAt(3); }
    public static int charSequenceCastIdentity() { CharSequence s = "sequence"; return ((String)s) == "sequence" ? 1 : 0; }
    public static int comparableLess() { Comparable<String> c = "abc"; return c.compareTo("abd"); }
    public static int comparableEqual() { Comparable<String> c = "abc"; return c.compareTo("abc"); }
    @SuppressWarnings({"rawtypes", "unchecked"})
    public static int bridgeCCE() { try { Comparable c = "abc"; c.compareTo(new MCLB0Box(1)); return 0; } catch (ClassCastException e) { return e == null ? -1 : 8; } }
    @SuppressWarnings({"rawtypes", "unchecked"})
    public static int bridgeNPE() { try { Comparable c = "abc"; c.compareTo(null); return 0; } catch (NullPointerException e) { return e == null ? -1 : 6; } }
    public static int directCompareNPE() { try { return "abc".compareTo(null); } catch (NullPointerException e) { return e == null ? -1 : 6; } }
    public static int nullReceiverNPE() { try { String s = null; return s.length(); } catch (NullPointerException e) { return e == null ? -1 : 6; } }
    public static int nullInterfaceNPE() { try { CharSequence s = null; return s.length(); } catch (NullPointerException e) { return e == null ? -1 : 6; } }

    public static int stringBeforeMixed(int x) { String s = "before"; int[] a = new int[2]; MCLB0Box b = new MCLB0Box(x); a[1] = b.value; return s.charAt(0) + a[1]; }
    public static int stringAfterMixed(int x) { int[] a = new int[2]; MCLB0Box b = new MCLB0Box(x); a[0] = b.value; String s = "after"; return a[0] + s.length(); }
    public static int exceptionThenString() { try { int[] a = null; return a.length; } catch (NullPointerException e) { return "caught".length(); } }
    public static int stringThenException() { String s = "saved"; try { int[] a = new int[1]; return a[2]; } catch (ArrayIndexOutOfBoundsException e) { return s == "saved" ? 5 : -1; } }
    public static int identityThroughObjectArray() { Object[] a = new Object[2]; a[0] = "array-id"; a[1] = new MCLB0Box(1); return a[0] == "array-id" ? ((String)a[0]).length() : -1; }
    public static int staticWithIntArray() { int[] a = new int[2]; a[1] = MCLB0Statics.NONFINAL.length(); return a[1] + (MCLB0Statics.NONFINAL == "nonfinal" ? 10 : 0); }
    public static int selectHash(int x) { String s = x == 0 ? "polygenelubricants" : "Minecraft"; return s.hashCode(); }
    public static int evaluationOrder() { side = 0; String a = mark(1) == 1 ? "ba" : "x"; int c = a.compareTo(mark(2) == 2 ? "bb" : "x"); return side * 10 + (c + 1); }
    public static int cpHitLoop(int n) { String first = "loop"; int sum = 0; for (int i = 0; i < n; i++) { String next = "loop"; if (next == first) sum += next.length(); } return sum; }
    public static int utf16Checksum() { String s = "A\000\u007f\u0080\u07ff\u0800\ud800\udc00\uffff"; int h = 0; for (int i = 0; i < s.length(); i++) h = h * 31 + s.charAt(i); return h ^ s.hashCode(); }

    public static int resetBetweenRun() { return ++MCLB0Statics.RUN_COUNT; }
    public static int boundaryLongLength() { return MCLB0Long.VALUE.length(); }
    public static int boundaryLongCompare() { return MCLB0Long.VALUE.compareTo(MCLB0Long.NEAR); }
}
