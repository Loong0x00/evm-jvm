final class RunImpl implements Runnable {
    static int invoked;
    public void run() { invoked = 1; }
}
