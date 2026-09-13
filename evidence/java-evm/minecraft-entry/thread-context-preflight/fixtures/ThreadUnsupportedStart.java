/** start is deliberately absent: singleton identity is not a scheduler. */
public final class ThreadUnsupportedStart {
    public static void main(String[] ignored) { Thread.currentThread().start(); }
}
