// Generated-only parent UTF-16 content probe, not a server class.
public final class TargetMain {
    public static int state;
    static { state = 11; }
    public static void main(String[] args) {
        state = state * 31 + args.length;
        for (int a = 0; a < args.length; ++a) {
            String s = args[a];
            state = state * 31 + s.length();
            for (int i = 0; i < s.length(); ++i) state = state * 31 + s.charAt(i);
        }
    }
}
