package regexprobe;
import java.util.regex.Pattern;
/** Mutation after matcher admission must still take the explicit surrogate refusal path. */
public final class RegexMutableSequenceRefusalProbe {
    private static final class Sequence implements CharSequence {
        private char value = 'a';
        public int length() { return 1; }
        public char charAt(int index) { if (index != 0) throw new IndexOutOfBoundsException(); return value; }
        public CharSequence subSequence(int start, int end) { if (start != 0 || end != 1) throw new IndexOutOfBoundsException(); return this; }
        public String toString() { return "a"; }
        void mutate(char next) { value = next; }
    }
    public static void main(String[] args) {
        Sequence input = new Sequence();
        java.util.regex.Matcher matcher = Pattern.compile("a").matcher(input);
        if (!matcher.matches()) throw new RuntimeException("initial match");
        input.mutate('\ud800');
        matcher.matches();
        throw new RuntimeException("surrogate mutation escaped profile refusal");
    }
}
