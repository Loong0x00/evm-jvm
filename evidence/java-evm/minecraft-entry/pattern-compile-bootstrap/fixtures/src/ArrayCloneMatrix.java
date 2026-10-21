public final class ArrayCloneMatrix {
    private static void require(boolean value) {
        if (!value) throw new IllegalArgumentException();
    }

    private static void primitiveArrays() {
        boolean[] booleans = new boolean[] {true, false};
        boolean[] booleansCopy = (boolean[]) booleans.clone();
        require(booleansCopy != booleans && booleansCopy.length == 2);
        booleansCopy[0] = false;
        require(booleans[0] && !booleansCopy[0]);

        byte[] bytes = new byte[] {-128, -1, 0, 127};
        byte[] bytesCopy = (byte[]) bytes.clone();
        require(bytesCopy != bytes && bytesCopy.length == 4);
        bytesCopy[0] = 0;
        require(bytes[0] == -128 && bytesCopy[0] == 0);

        char[] chars = new char[] {'\u0000', '\u0001', '\uffff'};
        char[] charsCopy = (char[]) chars.clone();
        require(charsCopy != chars && charsCopy.length == 3);
        charsCopy[2] = 'x';
        require(chars[2] == '\uffff' && charsCopy[2] == 'x');

        short[] shorts = new short[] {-32768, -1, 0, 32767};
        short[] shortsCopy = (short[]) shorts.clone();
        require(shortsCopy != shorts && shortsCopy.length == 4);
        shortsCopy[0] = 0;
        require(shorts[0] == -32768 && shortsCopy[0] == 0);

        int[] ints = new int[] {Integer.MIN_VALUE, -1, 0, Integer.MAX_VALUE};
        int[] intsCopy = (int[]) ints.clone();
        require(intsCopy != ints && intsCopy.length == 4);
        intsCopy[0] = 0;
        require(ints[0] == Integer.MIN_VALUE && intsCopy[0] == 0);

        long[] longs = new long[] {Long.MIN_VALUE, -1L, 0L, Long.MAX_VALUE};
        long[] longsCopy = (long[]) longs.clone();
        require(longsCopy != longs && longsCopy.length == 4);
        longsCopy[0] = 0L;
        require(longs[0] == Long.MIN_VALUE && longsCopy[0] == 0L);

        float[] floats = new float[] {
            Float.intBitsToFloat(0x7fc12345),
            Float.intBitsToFloat(0x80000000),
            Float.intBitsToFloat(0x00000000),
            Float.intBitsToFloat(0xff800000)
        };
        float[] floatsCopy = (float[]) floats.clone();
        require(floatsCopy != floats && floatsCopy.length == 4);
        require(Float.floatToRawIntBits(floatsCopy[0]) == 0x7fc12345);
        require(Float.floatToRawIntBits(floatsCopy[1]) == 0x80000000);
        require(Float.floatToRawIntBits(floatsCopy[2]) == 0x00000000);
        require(Float.floatToRawIntBits(floatsCopy[3]) == 0xff800000);
        floatsCopy[1] = 0.0f;
        require(Float.floatToRawIntBits(floats[1]) == 0x80000000);
        require(Float.floatToRawIntBits(floatsCopy[1]) == 0x00000000);

        double[] doubles = new double[] {
            Double.longBitsToDouble(0x7ff8000000001234L),
            Double.longBitsToDouble(0x8000000000000000L),
            Double.longBitsToDouble(0x0000000000000000L),
            Double.longBitsToDouble(0xfff0000000000000L)
        };
        double[] doublesCopy = (double[]) doubles.clone();
        require(doublesCopy != doubles && doublesCopy.length == 4);
        require(Double.doubleToRawLongBits(doublesCopy[0]) == 0x7ff8000000001234L);
        require(Double.doubleToRawLongBits(doublesCopy[1]) == 0x8000000000000000L);
        require(Double.doubleToRawLongBits(doublesCopy[2]) == 0x0000000000000000L);
        require(Double.doubleToRawLongBits(doublesCopy[3]) == 0xfff0000000000000L);
        doublesCopy[1] = 0.0d;
        require(Double.doubleToRawLongBits(doubles[1]) == 0x8000000000000000L);
        require(Double.doubleToRawLongBits(doublesCopy[1]) == 0x0000000000000000L);

        int[] empty = new int[0];
        int[] emptyCopy = (int[]) empty.clone();
        require(emptyCopy != empty && emptyCopy.length == 0);
    }

    private static void referenceArrays() {
        ArrayCloneCell first = new ArrayCloneCell(17);
        ArrayCloneCell[] cells = new ArrayCloneCell[] {first, null};
        ArrayCloneCell[] cellsCopy = (ArrayCloneCell[]) cells.clone();
        require(cellsCopy != cells && cellsCopy.length == 2);
        require(cellsCopy[0] == first && cellsCopy[1] == null);
        cellsCopy[0] = new ArrayCloneCell(3);
        require(cells[0] == first && cells[0].value == 17 && cellsCopy[0].value == 3);

        ArrayCloneCell[][] nested = new ArrayCloneCell[1][1];
        nested[0][0] = first;
        Object nestedResult = nested.clone();
        require(nestedResult instanceof ArrayCloneCell[][]);
        ArrayCloneCell[][] nestedCopy = (ArrayCloneCell[][]) nestedResult;
        require(nestedCopy != nested && nestedCopy[0] == nested[0]);
        nestedCopy[0][0].value = 29;
        require(nested[0][0].value == 29);
        nestedCopy[0] = null;
        require(nested[0] != null);

        Object[] covariant = new String[2];
        Object[] covariantCopy = (Object[]) covariant.clone();
        require(covariantCopy instanceof String[]);
        String[] stringCopy = (String[]) covariantCopy;
        require(stringCopy != covariant && stringCopy.length == 2);
        boolean caughtStore = false;
        try {
            covariantCopy[0] = new Object();
        } catch (ArrayStoreException expected) {
            caughtStore = true;
        }
        require(caughtStore && covariant[0] == null && covariantCopy[0] == null);

        Cloneable cloneable = cells.clone();
        java.io.Serializable serializable = cells.clone();
        require(cloneable != null && serializable != null);
    }

    private static void nullReceiver() {
        int[] absent = null;
        boolean caught = false;
        try {
            absent.clone();
        } catch (NullPointerException expected) {
            caught = true;
        }
        require(caught);
    }

    public static void main(String[] args) {
        primitiveArrays();
        referenceArrays();
        nullReceiver();
    }
}
