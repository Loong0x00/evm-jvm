package bundle.m3c.lazy;

public class LazyRoot {
    public static int inlinedConstant(int addend) {
        return ConstantHolder.VALUE + addend;
    }

    public static int ignoreProvidedInitializer(int value) {
        return value * 7 + 3;
    }
}
