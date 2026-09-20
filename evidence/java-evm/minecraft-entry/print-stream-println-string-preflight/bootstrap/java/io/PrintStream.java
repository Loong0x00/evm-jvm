package java.io;
/** Behavioral contract for the hand-assembled 243-byte Java 8 image.
 * The emitted Code probes line with a balanced monitor pair before its store,
 * so null takes ordinary guest NPE and cannot overwrite the prior reference. */
public class PrintStream {
    private String println;
    public PrintStream() {}
    public void println(String line) { synchronized (line) {} println = line; }
}
