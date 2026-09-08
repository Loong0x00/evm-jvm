package bundle.m5a.fields;

/** Narrow static/instance fields, hiding, finals, ConstantValue, and interface fields. */
public class FieldRoot {
    public static int staticDefaults(int value) {
        return FieldOwner.B + FieldOwner.S + FieldOwner.C + (FieldOwner.Z ? 1 : 0) + value;
    }

    public static int staticWrites(int value) {
        FieldOwner.B = (byte) value;
        FieldOwner.S = (short) (value * 257);
        FieldOwner.C = (char) (value - 1);
        FieldOwner.Z = (value & 1) != 0;
        return FieldOwner.B * 1000000 + FieldOwner.S * 10 + FieldOwner.C + (FieldOwner.Z ? 1 : 0);
    }

    public static int staticCompound(int value) {
        FieldOwner.B = (byte) value;
        FieldOwner.S = (short) value;
        FieldOwner.C = (char) value;
        FieldOwner.B += 129;
        FieldOwner.S *= 257;
        FieldOwner.C -= 65537;
        return FieldOwner.B * 1000000 + FieldOwner.S * 10 + FieldOwner.C;
    }

    public static int instanceDefaults(int value) {
        FieldOwner owner = new FieldOwner();
        return owner.b + owner.s + owner.c + (owner.z ? 1 : 0) + value;
    }

    public static int instanceWrites(int value) {
        FieldOwner owner = new FieldOwner();
        owner.b = (byte) value;
        owner.s = (short) (value + 32768);
        owner.c = (char) (value - 65537);
        owner.z = (value & 1) != 0;
        return owner.b * 1000000 + owner.s * 10 + owner.c + (owner.z ? 1 : 0);
    }

    public static int hiddenStatic(int value) {
        FieldBase.B = (byte) value;
        FieldChild.B = (byte) (value + 1);
        FieldBase.C = (char) (value - 1);
        FieldChild.C = (char) (value + 2);
        return FieldBase.B * 1000000 + FieldChild.B * 10000 + FieldBase.C * 10 + FieldChild.C;
    }

    public static int hiddenInstance(int value) {
        FieldChild child = new FieldChild((byte) value, (short) (value + 1));
        return child.readBoth();
    }

    public static int finalConstructorFields(int value) {
        FinalFields fields = new FinalFields((byte) value, (short) (value * 257),
            (char) (value - 1), (value & 1) != 0);
        return fields.pack();
    }

    public static int classConstants(int value) {
        return ConstantFields.CONST_B * 1000000 + ConstantFields.CONST_S * 10
            + ConstantFields.CONST_C + (ConstantFields.CONST_Z ? 1 : 0) + value;
    }

    public static int interfaceConstants(int value) {
        return ConstantFace.CONST_B * 1000000 + ConstantFace.CONST_S * 10
            + ConstantFace.CONST_C + (ConstantFace.CONST_Z ? 1 : 0) + value;
    }

    public static int interfaceDynamicByte(int value) {
        return DynamicFace.B * 100 + FieldState.trace + value;
    }

    public static int interfaceDynamicShort(int value) {
        return DynamicFace.S * 100 + FieldState.trace + value;
    }

    public static int interfaceDynamicChar(int value) {
        return DynamicFace.C * 100 + FieldState.trace + value;
    }

    public static int interfaceDynamicBoolean(int value) {
        return (DynamicFace.Z ? 1000 : 0) + FieldState.trace * 10 + value;
    }

    public static int inheritedInterfaceField(int value) {
        return DynamicChild.B * 100 + FieldState.trace + value;
    }

    public static int hiddenInterfaceFields(int value) {
        return HiddenParent.B * 10000 + HiddenChild.B * 100 + FieldState.trace + value;
    }

    public static int actualOwnerThroughChild(int value) {
        return FieldStaticChild.INHERITED_B * 100 + FieldState.trace + value;
    }
}

class FieldOwner {
    static byte B;
    static short S;
    static char C;
    static boolean Z;
    byte b;
    short s;
    char c;
    boolean z;
}

class FieldBase {
    static byte B;
    static char C;
    byte b;
    FieldBase(byte value) { b = value; }
}
class FieldChild extends FieldBase {
    static byte B;
    static char C;
    short b;
    FieldChild(byte parent, short child) { super(parent); b = child; }
    int readBoth() { return super.b * 100000 + b; }
}

class FinalFields {
    final byte b;
    final short s;
    final char c;
    final boolean z;
    FinalFields(byte b, short s, char c, boolean z) { this.b = b; this.s = s; this.c = c; this.z = z; }
    int pack() { return b * 1000000 + s * 10 + c + (z ? 1 : 0); }
}

class ConstantFields {
    static final byte CONST_B = (byte) 255;
    static final short CONST_S = (short) 65535;
    static final char CONST_C = (char) 65535;
    static final boolean CONST_Z = true;
}
interface ConstantFace {
    byte CONST_B = (byte) 255;
    short CONST_S = (short) 65535;
    char CONST_C = (char) 65535;
    boolean CONST_Z = true;
}

class FieldState {
    static int trace;
    static int mark(int digit, int value) { trace = trace * 10 + digit; return value; }
    static boolean markBoolean(int digit, boolean value) { trace = trace * 10 + digit; return value; }
}
interface DynamicFace {
    byte B = (byte) FieldState.mark(1, 255);
    short S = (short) FieldState.mark(2, 65535);
    char C = (char) FieldState.mark(3, -1);
    boolean Z = FieldState.markBoolean(4, true);
}
interface DynamicChild extends DynamicFace {}
interface HiddenParent { byte B = (byte) FieldState.mark(5, 130); }
interface HiddenChild extends HiddenParent { byte B = (byte) FieldState.mark(6, 131); }
class FieldStaticParent { static byte INHERITED_B = (byte) FieldState.mark(7, 132); }
class FieldStaticChild extends FieldStaticParent {}
