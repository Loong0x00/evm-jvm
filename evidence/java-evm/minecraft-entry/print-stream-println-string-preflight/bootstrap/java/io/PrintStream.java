package java.io;
/** Exact source-level contract for the hand-assembled 239-byte Java 8 image. */
public class PrintStream {
    private String println;
    public PrintStream() {}
    public void println(String line) { println = line; }
}
