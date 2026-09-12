// HOST-TEST-ONLY Java 8 oracle. It is never part of the uploaded ZIP or EVM execution.
public final class Oracle {
    public static void main(String[] argv) {
        int mode = Integer.parseInt(argv[0]);
        try {
            System.out.println(mode + ":R:" + Launcher.run(mode));
        } catch (Throwable t) {
            System.out.println(mode + ":X:" + t.getClass().getName());
        }
    }
}
