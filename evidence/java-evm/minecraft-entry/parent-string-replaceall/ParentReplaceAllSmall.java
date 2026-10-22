public final class ParentReplaceAllSmall {
    public static void main(String[] args) {
        String result = "a!b".replaceAll("[^a-z]", "");
        if (!result.equals("ab")) throw new ArithmeticException();
        if (!"aa".replaceAll("a", "$0!").equals("a!a!")) throw new ArithmeticException();
    }
}
