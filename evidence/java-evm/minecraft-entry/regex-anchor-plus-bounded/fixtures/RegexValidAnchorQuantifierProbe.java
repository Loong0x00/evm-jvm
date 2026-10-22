package regexprobe;
import java.util.regex.Pattern;
/** Valid Java 8 syntax outside PAT2; EVM must raw-refuse, never fake PSE/no-match. */
public final class RegexValidAnchorQuantifierProbe {
    public static void main(String[] args) {
        String regex = args.length == 0 ? "^+" : args[0];
        Pattern.compile(regex);
        throw new RuntimeException("valid unsupported anchor quantifier returned");
    }
}
