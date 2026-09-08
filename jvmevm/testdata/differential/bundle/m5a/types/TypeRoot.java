package bundle.m5a.types;

import java.io.Serializable;

/** Primitive-array identity, ranks, marker interfaces, casts, and compatible nested stores. */
public class TypeRoot {
    public static int byteAsObject(int value) { Object object = new byte[1]; return object instanceof byte[] ? value : -1; }
    public static int booleanAsObject(int value) { Object object = new boolean[1]; return object instanceof boolean[] ? value : -1; }
    public static int charAsObject(int value) { Object object = new char[1]; return object instanceof char[] ? value : -1; }
    public static int shortAsObject(int value) { Object object = new short[1]; return object instanceof short[] ? value : -1; }

    public static int allPrimitiveMarkers(int value) {
        Object b = new byte[0], z = new boolean[0], c = new char[0], s = new short[0];
        return b instanceof Cloneable && b instanceof Serializable
            && z instanceof Cloneable && z instanceof Serializable
            && c instanceof Cloneable && c instanceof Serializable
            && s instanceof Cloneable && s instanceof Serializable ? value : -1;
    }

    public static int byteMatrixAsObjectArray(int value) {
        Object object = new byte[2][]; return object instanceof Object[] ? value : -1;
    }
    public static int byteLeafNotObjectArray(int value) {
        Object object = new byte[2]; return object instanceof Object[] ? -1 : value;
    }
    public static int byteBooleanDistinct(int value) {
        Object object = new boolean[1]; return object instanceof byte[] ? -1 : value;
    }
    public static int byteIntMatrixDistinct(int value) {
        Object object = new byte[1][1]; return object instanceof int[][] ? -1 : value;
    }
    public static int charShortDistinct(int value) {
        Object object = new char[1]; return object instanceof short[] ? -1 : value;
    }
    public static int rankDistinct(int value) {
        Object object = new byte[1][1]; return object instanceof byte[] || !(object instanceof byte[][]) ? -1 : value;
    }

    public static int byteMatrixAsCloneableArray(int value) {
        Object object = new byte[1][1]; return object instanceof Cloneable[] ? value : -1;
    }
    public static int byteMatrixAsSerializableArray(int value) {
        Object object = new byte[1][1]; return object instanceof Serializable[] ? value : -1;
    }
    public static int compatibleNestedStore(int value) {
        byte[][] actual = new byte[1][];
        Object[] widened = actual;
        byte[] leaf = new byte[1]; leaf[0] = (byte) value; widened[0] = leaf;
        return actual[0][0];
    }
    public static int castByteIdentity(int value) {
        byte[] original = new byte[1]; original[0] = (byte) value;
        Object object = original; byte[] restored = (byte[]) object;
        return restored == original ? restored[0] : -999;
    }
    public static int castMatrixToObjectArray(int value) {
        byte[][] matrix = new byte[1][1]; matrix[0][0] = (byte) value;
        Object object = matrix; Object[] outer = (Object[]) object; byte[] row = (byte[]) outer[0];
        return row[0];
    }
}
