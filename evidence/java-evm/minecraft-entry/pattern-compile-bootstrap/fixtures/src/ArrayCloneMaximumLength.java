public final class ArrayCloneMaximumLength {
    private static void require(boolean value) {
        if (!value) throw new IllegalArgumentException();
    }

    public static void main(String[] args) {
        double[] original = new double[65536];
        original[0] = Double.longBitsToDouble(0x7ff8000000005678L);
        original[1] = Double.longBitsToDouble(0x8000000000000000L);
        original[65535] = Double.longBitsToDouble(0xfff0000000000000L);
        double[] copy = (double[]) original.clone();
        require(copy != original && copy.length == 65536);
        require(Double.doubleToRawLongBits(copy[0]) == 0x7ff8000000005678L);
        require(Double.doubleToRawLongBits(copy[1]) == 0x8000000000000000L);
        require(Double.doubleToRawLongBits(copy[65535]) == 0xfff0000000000000L);
        copy[1] = 0.0d;
        require(Double.doubleToRawLongBits(original[1]) == 0x8000000000000000L);
        require(Double.doubleToRawLongBits(copy[1]) == 0L);
    }
}
