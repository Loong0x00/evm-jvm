import java.util.regex.Pattern;
public final class ParentRegexRefusal {
    public static void main(String[] args) {
        Pattern.compile("^+");
        throw new ArithmeticException();
    }
}
