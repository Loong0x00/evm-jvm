// Generated Java 8 preflight fixture only.
public final class LinkMain extends LinkBase implements LinkMarker {
    static int state = base + 5;
    public static void main(String[] args) {
        // Both non-ASCII literals are consumed as UTF-16 code units, not merely length.
        state += args.length + args[0].charAt(0) + args[1].charAt(0);
    }
}
