package java.io;
/** Exact hand-assembled Java 8 image contract; no host output or conversion. */
public class PrintStream {
    private String println;
    private char print;
    public PrintStream() {}
    public void println(String line) { synchronized (line) {} println = line; }
    public void print(char codeUnit) { print = codeUnit; }
}
