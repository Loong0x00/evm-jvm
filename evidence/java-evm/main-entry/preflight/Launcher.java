// Generated Java 8 fixture only; not a server/JAR patch.
public final class Launcher {
    public static int run(int mode) {
        if (mode == 0) {
            String[] a = new String[0];
            TargetMain.main(a);
            return TargetMain.state;
        }
        if (mode == 1) {
            String[] a = new String[] { "ASCII", "arg" };
            TargetMain.main(a);
            return TargetMain.state;
        }
        if (mode == 2) {
            String[] a = new String[] { "\u03bb", "\u2603" };
            TargetMain.main(a);
            return TargetMain.state;
        }
        if (mode == 3) {
            TargetMain.main(null); // genuine guest null-array NPE
            return TargetMain.state;
        }
        return -1;
    }
}
