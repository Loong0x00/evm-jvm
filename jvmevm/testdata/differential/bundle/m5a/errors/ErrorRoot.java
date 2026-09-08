package bundle.m5a.errors;

/** Genuine narrow-array Java exception outcomes and ordering probes. */
public class ErrorRoot {
    public static int negativeByteArray(int size) { return new byte[size].length; }
    public static int negativeBooleanArray(int size) { return new boolean[size].length; }
    public static int negativeCharArray(int size) { return new char[size].length; }
    public static int negativeShortArray(int size) { return new short[size].length; }

    public static int nullByteReadBeforeBounds(int index) { byte[] values = null; return values[index]; }
    public static int nullBooleanWriteBeforeBounds(int index) { boolean[] values = null; values[index] = true; return 0; }
    public static int nullCharReadBeforeBounds(int index) { char[] values = null; return values[index]; }
    public static int nullShortWriteBeforeBounds(int index) { short[] values = null; values[index] = 1; return 0; }

    public static int byteNegativeIndex(int index) { byte[] values = new byte[1]; return values[index]; }
    public static int booleanEqualLengthIndex(int index) { boolean[] values = new boolean[1]; return values[index] ? 1 : 0; }
    public static int charLargeIndex(int index) { char[] values = new char[2]; return values[index]; }
    public static int shortStoreEqualLength(int index) { short[] values = new short[2]; values[index] = 1; return 0; }

    public static int castBooleanToByte(int value) { Object object = new boolean[1]; return ((byte[]) object)[0] + value; }
    public static int castByteMatrixToIntMatrix(int value) { Object object = new byte[1][1]; return ((int[][]) object)[0][0] + value; }

    public static int storeBooleanLeafInByteMatrix(int value) {
        byte[][] actual = new byte[1][]; Object[] widened = actual; widened[0] = new boolean[1]; return value;
    }
    public static int storeIntLeafInByteMatrix(int value) {
        byte[][] actual = new byte[1][]; Object[] widened = actual; widened[0] = new int[1]; return value;
    }
    public static int storeByteLeafInBooleanMatrix(int value) {
        boolean[][] actual = new boolean[1][]; Object[] widened = actual; widened[0] = new byte[1]; return value;
    }
}
