package java.io;
/** Exact hand-assembled Java 8 image contract; no host output or conversion. */
public class PrintStream extends OutputStream {
    private String println;
    private char print;
    public PrintStream() { super(); }
    public void println(String line) { synchronized (line) {} println = line; }
    public void print(char codeUnit) { print = codeUnit; }
    /** Required concrete override; stores only the low UTF-16 code unit in the guest sink. */
    public void write(int value) { print = (char) (value & 0xff); }
}
