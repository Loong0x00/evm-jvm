// Generated Java 8 fixture only. Observable static initialization and void main.
public final class TargetMain {
    public static int state;
    static { state = 11; }

    public static void main(String[] args) {
        state = state * 31 + args.length;
        if (args.length != 0) {
            state += args[0].length() * 7;
            state += args[args.length - 1].length();
        }
    }
}
