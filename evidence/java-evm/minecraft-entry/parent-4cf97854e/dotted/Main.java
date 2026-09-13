package dotted;
public class Main {
    static int touched;
    static Class<?> saved = Target.class;
    public static void main(String[] args) {
        Class<?> again = Target.class;
        if (saved != again || touched != 0 || !again.getName().equals("dotted.Target"))
            throw new RuntimeException();
        Target.touch();
        if (touched != 1) throw new RuntimeException();
    }
}
