import java.util.regex.Pattern;

/** The Java 8 flags overload is intentionally not in this measured bootstrap. */
public final class PatternOmittedCompileFlags {
    public static void main(String[] args) {
        Pattern.compile("abc", Pattern.CASE_INSENSITIVE);
    }
}
