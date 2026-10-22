import java.util.regex.Pattern;
import java.util.regex.Matcher;
public final class ParentRegexMutationRefusal {
    static final class Text implements CharSequence {
        char c = 'a';
        public int length() { return 1; }
        public char charAt(int i) { return c; }
        public CharSequence subSequence(int a, int b) { return this; }
    }
    public static void main(String[] args) {
        Text text = new Text();
        Matcher matcher = Pattern.compile("^[a-z]+$").matcher(text);
        text.c = (char) 0xd800;
        matcher.matches();
        throw new ArithmeticException();
    }
}
