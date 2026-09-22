#!/usr/bin/env python3
"""Build trusted generated Java-8 guest-stack-trace probes only.

This script never reads an original JAR, Minecraft data, or a world.  The optional
host JVM run is only a differential sanity check for these locally generated
sources; it is not an EVM execution path.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-classcount62-byte376794-focused-fixtures-")
assert not out.exists()
out.mkdir()
sources_root = out / "src"; classes_root = out / "classes"
sources_root.mkdir(); classes_root.mkdir()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
rows = {}

def build(label, sources, entries, host_main=None):
    source_dir = sources_root / label; class_dir = classes_root / label
    source_dir.mkdir(); class_dir.mkdir()
    for name, body in sources.items():
        path = source_dir / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", class_dir,
                    *map(str, sorted(source_dir.rglob("*.java")))], check=True)
    if host_main is not None:
        subprocess.run([java, "-cp", class_dir, host_main], check=True)
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for name in entries:
            data = (class_dir / name).read_bytes()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)
    row = {
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": 94,
        "totalClassBytes": sum((class_dir / name).stat().st_size for name in entries),
        "classBytes": {name: (class_dir / name).stat().st_size for name in entries},
        "classSHA256": {name: hashlib.sha256((class_dir / name).read_bytes()).hexdigest() for name in entries},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row

# Top-first caller frames must be leaf, nested, then main.  The checks deliberately
# index all three elements, as ReflectionUtil's prior failure did, then verify the
# two real dotted class/method names and the non-native element API.
stack_source = """public final class GuestStackTraceMain {
  static int result;
  static void leaf() {
    Throwable t = new Throwable();
    StackTraceElement[] a = t.getStackTrace();
    StackTraceElement[] b = t.getStackTrace();
    if (a == null || b == null || a == b || a.length != 3 || b.length != 3) throw new Error();
    if (a[0] == b[0]) throw new Error();
    if (!a[0].getClassName().equals(\"GuestStackTraceMain\") || !a[0].getMethodName().equals(\"leaf\")) throw new Error();
    if (!a[1].getClassName().equals(\"GuestStackTraceMain\") || !a[1].getMethodName().equals(\"nested\")) throw new Error();
    if (!a[2].getClassName().equals(\"GuestStackTraceMain\") || !a[2].getMethodName().equals(\"main\")) throw new Error();
    if (a[0].isNativeMethod() || a[1].isNativeMethod() || a[2].isNativeMethod()) throw new Error();
    result = 7;
  }
  static void nested() { leaf(); }
  public static void main(String[] ignored) { nested(); }
}
"""
# HotSpot may legally reuse immutable host StackTraceElement objects across
# repeated calls, while this bounded guest profile explicitly does not; therefore
# the freshness witness intentionally has no host-identity oracle.
build("guest-stack", {"GuestStackTraceMain.java": stack_source}, ["GuestStackTraceMain.class"])

# A two-frame probe keeps a distinct depth and catches accidental constant
# cardinality/order while remaining host-oracle compatible.
two_source = """public final class GuestStackTraceTwoMain {
  static int result;
  static void leaf() {
    StackTraceElement[] a = new Throwable().getStackTrace();
    if (a.length != 2) throw new Error();
    if (!a[0].getClassName().equals(\"GuestStackTraceTwoMain\") || !a[0].getMethodName().equals(\"leaf\")) throw new Error();
    if (!a[1].getClassName().equals(\"GuestStackTraceTwoMain\") || !a[1].getMethodName().equals(\"main\")) throw new Error();
    result = 7;
  }
  public static void main(String[] ignored) { leaf(); }
}
"""
build("guest-stack-two", {"GuestStackTraceTwoMain.java": two_source}, ["GuestStackTraceTwoMain.class"], "GuestStackTraceTwoMain")

# Thread keeps its separately bounded zero-length Java implementation.  It has no
# host oracle because the host Thread API intentionally has different semantics.
thread_source = """public final class ThreadStackTraceUnchangedMain {
  static int result;
  public static void main(String[] ignored) {
    StackTraceElement[] a = Thread.currentThread().getStackTrace();
    StackTraceElement[] b = Thread.currentThread().getStackTrace();
    if (a == null || b == null || a == b || a.length != 0 || b.length != 0) throw new Error();
    result = 7;
  }
}
"""
build("thread-empty", {"ThreadStackTraceUnchangedMain.java": thread_source}, ["ThreadStackTraceUnchangedMain.class"])

# No Throwable/StackTraceElement active use: both remain absent from initialization
# state even though their fixed bootstrap images are installed.
build("uninitialized", {"UninitializedMain.java": "public final class UninitializedMain { static int result; public static void main(String[] a) { result = 7; } }\n"}, ["UninitializedMain.class"], "UninitializedMain")

# Canonical bootstrap ownership rejection controls.  They are compiled but never
# executed by the host JVM and are supplied only to the generated EVM harness.
build("raw-throwable", {
    "RawThrowableMain.java": "public final class RawThrowableMain { public static void main(String[] a) {} }\n",
    "java/lang/Throwable.java": "package java.lang; public class Throwable { public Throwable() {} }\n",
}, ["RawThrowableMain.class", "java/lang/Throwable.class"])
build("raw-stack-trace-element", {
    "RawStackTraceElementMain.java": "public final class RawStackTraceElementMain { public static void main(String[] a) {} }\n",
    "java/lang/StackTraceElement.java": "package java.lang; public final class StackTraceElement { public StackTraceElement() {} }\n",
}, ["RawStackTraceElementMain.class", "java/lang/StackTraceElement.class"])

# Exact String.substring(int) focus. These inputs use only Java UTF-16 code
# units and trusted generated Java-8 sources; no archive/resource input exists.
utf16_source = """public final class SubstringUtf16Main {
  static int result;
  public static void main(String[] ignored) {
    String source = "A\\uD83D\\uDE00B";
    String suffix = source.substring(1);
    if (suffix == source || suffix.length() != 3) throw new Error();
    if (suffix.charAt(0) != '\\uD83D' || suffix.charAt(1) != '\\uDE00' || suffix.charAt(2) != 'B') throw new Error();
    if (!suffix.equals("\\uD83D\\uDE00B")) throw new Error();
    if (suffix.substring(2).charAt(0) != 'B') throw new Error();
    result = 7;
  }
}
"""
build("substring-utf16", {"SubstringUtf16Main.java": utf16_source}, ["SubstringUtf16Main.class"], "SubstringUtf16Main")

ascii_empty_source = """public final class SubstringAsciiEmptyMain {
  static int result;
  public static void main(String[] ignored) {
    String source = "abcd";
    String suffix = source.substring(1);
    String empty = source.substring(source.length());
    if (suffix == source || suffix.length() != 3 || suffix.charAt(0) != 'b' || suffix.charAt(2) != 'd') throw new Error();
    if (!suffix.equals("bcd") || empty == source || !empty.isEmpty() || empty.length() != 0) throw new Error();
    if (empty == "") throw new Error();
    result = 7;
  }
}
"""
build("substring-ascii-empty", {"SubstringAsciiEmptyMain.java": ascii_empty_source}, ["SubstringAsciiEmptyMain.class"], "SubstringAsciiEmptyMain")

identity_source = """public final class SubstringIdentityMain {
  static int result;
  public static void main(String[] ignored) {
    String source = "xyz";
    String zero = source.substring(0);
    String left = source.substring(1);
    String right = source.substring(1);
    if (zero != source || left == source || right == source || left == right) throw new Error();
    if (!left.equals("yz") || !right.equals("yz")) throw new Error();
    result = 7;
  }
}
"""
build("substring-identity-fresh", {"SubstringIdentityMain.java": identity_source}, ["SubstringIdentityMain.class"], "SubstringIdentityMain")

empty_receiver_source = """public final class SubstringEmptyReceiverMain {
  static int result;
  public static void main(String[] ignored) {
    String source = "";
    if (source.substring(0) != source || source.substring(source.length()) != source) throw new Error();
    result = 7;
  }
}
"""
build("substring-empty-receiver", {"SubstringEmptyReceiverMain.java": empty_receiver_source}, ["SubstringEmptyReceiverMain.class"], "SubstringEmptyReceiverMain")

# Invalid begins deliberately remain the one explicit profile refusal. They are
# not host-oracle cases because stock Java supplies a different exception class.
for label, class_name, expression in (
    ("substring-invalid-negative", "SubstringInvalidNegativeMain", '"abc".substring(-1)'),
    ("substring-invalid-past-end", "SubstringInvalidPastEndMain", '"abc".substring(4)'),
):
    source = "public final class %s { public static void main(String[] ignored) { %s; } }\n" % (class_name, expression)
    build(label, {class_name + ".java": source}, [class_name + ".class"])

# The two-argument overload remains absent and must resolve as the retained
# atomic member/profile refusal rather than broadening this one-argument slice.
omitted_source = "public final class SubstringTwoArgOmittedMain { public static void main(String[] ignored) { \"abc\".substring(0, 1); } }\n"
build("substring-twoarg-omitted", {"SubstringTwoArgOmittedMain.java": omitted_source}, ["SubstringTwoArgOmittedMain.class"])

# Every successful nonzero suffix consumes exactly one char[] and String. The
# 1024th ordinary allocation attempt must raise the existing catchable OOME
# without assigning a partial result; `last` remains the 1023rd complete suffix.
oom_source = """public final class SubstringOomMain {
  static int result;
  public static void main(String[] ignored) {
    String source = "ab";
    String last = source;
    int count = 0;
    try {
      for (;;) { last = source.substring(1); count++; }
    } catch (OutOfMemoryError expected) {
      // The already-live literal and bounded exception registry consume the
      // two retained ordinary-array slots; 1022 fresh suffixes fit exactly.
      if (count != 1022 || last == source || last.length() != 1 || last.charAt(0) != 'b') throw new Error();
      result = count;
    }
  }
}
"""
build("substring-oom-atomic", {"SubstringOomMain.java": oom_source}, ["SubstringOomMain.class"])

# Narrow current focus: bounded PrintStream(OutputStream), with no
# FilterOutputStream field or forwarding. The local stub exists only to compile
# trusted generated Java-8 bytecode; it is never bundled or executed by host Java.
PRINT_STREAM_OUTPUT_STREAM_STUB = """package java.io;
public class PrintStream extends OutputStream {
  public PrintStream() {}
  public PrintStream(OutputStream sink) {}
  public void println(String value) {}
  public void print(char value) {}
  public void write(int value) {}
}
"""
constructor_source = """public final class PrintStreamOutputStreamConstructorMain {
  static java.io.PrintStream direct;
  static java.io.PrintStream child;
  static java.io.OutputStream sink;
  static String directLine;
  static String childLine;
  static int forwarded;
  static int result;
  static final class Sink extends java.io.OutputStream {
    public void write(int value) { forwarded = value; }
  }
  static final class Child extends java.io.PrintStream {
    Child(java.io.OutputStream value) { super(value); }
  }
  public static void main(String[] ignored) {
    sink = new Sink();
    direct = new java.io.PrintStream(sink);
    child = new Child(sink);
    directLine = "constructor-direct-sink";
    childLine = "constructor-child-sink";
    direct.println(directLine);
    child.println(childLine);
    direct.print('D');
    child.write(0x1234);
    if (!(direct instanceof java.io.OutputStream) || !(child instanceof java.io.PrintStream)) throw new Error();
    if (direct == child || forwarded != 0) throw new Error();
    result = 7;
  }
}
"""
build("printstream-outputstream-constructor", {
    "java/io/PrintStream.java": PRINT_STREAM_OUTPUT_STREAM_STUB,
    "PrintStreamOutputStreamConstructorMain.java": constructor_source,
}, ["PrintStreamOutputStreamConstructorMain.class", "PrintStreamOutputStreamConstructorMain$Child.class", "PrintStreamOutputStreamConstructorMain$Sink.class"])

# The null path must be the interpreter's ordinary null receiver NPE from the
# exact Object.getClass check, not a host exception or a fabricated result.
null_source = """public final class PrintStreamOutputStreamConstructorNullMain {
  static java.io.PrintStream stream;
  static int caught;
  static int result;
  public static void main(String[] ignored) {
    try { stream = new java.io.PrintStream((java.io.OutputStream) null); throw new Error(); }
    catch (NullPointerException expected) { caught = 1; }
    if (stream != null || caught != 1) throw new Error();
    result = 7;
  }
}
"""
build("printstream-outputstream-constructor-null", {
    "java/io/PrintStream.java": PRINT_STREAM_OUTPUT_STREAM_STUB,
    "PrintStreamOutputStreamConstructorNullMain.java": null_source,
}, ["PrintStreamOutputStreamConstructorNullMain.class"])

# No direct class use: the constructor addition cannot initialize either side
# of the retained direct-superclass edge.
build("printstream-outputstream-constructor-uninitialized", {
    "PrintStreamOutputStreamConstructorUninitializedMain.java": "public final class PrintStreamOutputStreamConstructorUninitializedMain { static int result; public static void main(String[] ignored) { result = 7; } }\n",
}, ["PrintStreamOutputStreamConstructorUninitializedMain.class"], "PrintStreamOutputStreamConstructorUninitializedMain")

# The only new surface: all transitions are asserted inside guest bytecode. It
# deliberately has no host-JVM oracle because host System.setOut mutates process
# state. The final reset proves the original guest out identity survives after
# direct, subclass, and null replacement; every intermediate assertion proves
# System.err stays unchanged and no output behavior is involved.
setout_source = """public final class SystemSetOutMain {
  static java.io.PrintStream original;
  static java.io.PrintStream err;
  static java.io.PrintStream direct;
  static java.io.PrintStream child;
  static java.io.OutputStream sink;
  static int result;
  static final class Sink extends java.io.OutputStream {
    public void write(int value) {}
  }
  static final class Child extends java.io.PrintStream {
    Child(java.io.OutputStream value) { super(value); }
  }
  public static void main(String[] ignored) {
    original = System.out;
    err = System.err;
    if (original == null || err == null || original == err) throw new Error();
    sink = new Sink();
    direct = new java.io.PrintStream(sink);
    child = new Child(sink);
    System.setOut(direct);
    if (System.out != direct || System.err != err) throw new Error();
    System.setOut(child);
    if (System.out != child || System.err != err) throw new Error();
    System.setOut(null);
    if (System.out != null || System.err != err) throw new Error();
    System.setOut(original);
    if (System.out != original || System.err != err || System.out == System.err) throw new Error();
    result = 7;
  }
}
"""
build("system-setout", {"SystemSetOutMain.java": setout_source}, [
    "SystemSetOutMain.class", "SystemSetOutMain$Child.class", "SystemSetOutMain$Sink.class",
])

# A raw same-named class carrying the exact native declaration must be rejected
# during bootstrap ownership validation before it can acquire binding16.
build("raw-system-setout", {
    "RawSystemSetOutReplacementMain.java": "public final class RawSystemSetOutReplacementMain { public static void main(String[] ignored) { System.setOut(null); } }\n",
    "java/lang/System.java": "package java.lang; public final class System { public static native void setOut(java.io.PrintStream stream); }\n",
}, ["RawSystemSetOutReplacementMain.class", "java/lang/System.class"])
