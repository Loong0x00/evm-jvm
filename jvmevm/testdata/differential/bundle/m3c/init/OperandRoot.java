package bundle.m3c.init;

public class OperandRoot {
    public static int getWithPrefix(int prefix) {
        return prefix * 100 + OperandOwner.value;
    }

    public static int putWithPrefix(int prefix, int value) {
        return prefix * 100 + (OperandOwner.value = value * 3 + 1);
    }

    public static int callWithPrefix(int prefix, int first, int second) {
        return prefix * 10000 + OperandOwner.combine(first, second);
    }

    public static int putThenCheckInitialization(int value) {
        OperandOwner.value = value;
        return OperandOwner.runs * 1000 + OperandOwner.value;
    }
}
