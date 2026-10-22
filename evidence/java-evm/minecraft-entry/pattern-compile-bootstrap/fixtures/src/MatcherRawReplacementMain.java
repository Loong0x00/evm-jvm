import java.util.regex.Pattern;

/** Compiled only to prove a caller cannot replace the authenticated Matcher image. */
public final class MatcherRawReplacementMain {
    public static void main(String[] args) {
        Pattern.compile("a").matcher("a").replaceAll("b");
    }
}
