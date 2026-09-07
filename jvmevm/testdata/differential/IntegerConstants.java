public class IntegerConstants {
    public static int positiveLdc() {
        return 123456789;
    }

    public static int negativeLdc() {
        return -123456789;
    }

    public static int maxLdc() {
        return 2147483647;
    }

    public static int minLdc() {
        return -2147483648;
    }

    public static int highBitPattern() {
        return 0x80010001;
    }

    public static int alternatingBits() {
        return 0x5a5aa5a5;
    }

    public static int addLdc(int value) {
        return value + 1000000000;
    }
}
