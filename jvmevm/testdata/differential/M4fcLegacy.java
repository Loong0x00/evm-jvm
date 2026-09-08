/** Legacy single-class-path interface-static roots and callers. */
public interface M4fcLegacy {
    static int own(int value) { return value + 3; }
    static int zero() { return 17; }
    static int combine(int first, int second) { return first * 10 + second; }
    static int callsOwn(int value) { return own(value) + zero(); }
    static int callsClass(int value) { return M4fcLegacyClass.ordinary(value); }
    static int classCallsInterface(int value) { return M4fcLegacyClass.callInterface(value); }
    static int callsDefault(int value) { return M4fcLegacyClass.defaultCall(value); }
    static M4fcLegacyBox make(int value) { return new M4fcLegacyBox(value + 5); }
    static M4fcLegacyBox identity(M4fcLegacyBox value) { return value; }
    static int[] array(int value) { int[] result = new int[2]; result[0] = value; result[1] = value + 1; return result; }
    static M4fcLegacyBox nullBox() { return null; }
    static int nullArgument(M4fcLegacyBox value, int fallback) { return value == null ? fallback : value.value; }
    static int factoryValue(int value) { return make(value).value; }
    static int identityValue(int value) { M4fcLegacyBox box = new M4fcLegacyBox(value); return identity(box) == box ? value : -1; }
    static int arrayValue(int value) { int[] values = array(value); return values[0] * 10 + values[1]; }
    static int nullReturnValue(int value) { return nullBox() == null ? value : -1; }
    static int nullArgumentValue(int value) { return nullArgument(null, value); }

    default int throughDefault(int value) { return M4fcLegacy.own(value) + 1; }
}

class M4fcLegacyBox {
    int value;
    M4fcLegacyBox(int value) { this.value = value; }
}

class M4fcLegacyImpl implements M4fcLegacy {}

class M4fcLegacyClass {
    static int callInterface(int value) { return M4fcLegacy.combine(value, value + 1); }
    static int ordinary(int value) { return value * 2; }
    static int defaultCall(int value) { return new M4fcLegacyImpl().throughDefault(value); }
}
