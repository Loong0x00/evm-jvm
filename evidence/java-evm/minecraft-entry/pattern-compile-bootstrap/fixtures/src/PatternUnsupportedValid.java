import java.util.regex.Pattern;

/** Valid Java 8 regex outside the bounded compiler grammar: quantifier. */
public final class PatternUnsupportedValid {
    public static void main(String[] args) {
        Pattern.compile("a+");
    }
}
