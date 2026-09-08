package bundle.m4fc.transport;

/** Reference and array values cross interface-static call boundaries but roots remain int-only. */
public class TransportRoot {
    public static int factory(int value) { return TransportStatics.make(value).value; }
    public static int identity(int value) { TransportBox box = new TransportBox(value); return TransportStatics.identity(box) == box ? box.value : -1; }
    public static int objectIdentity(int value) { TransportBox box = new TransportBox(value); return TransportStatics.objectIdentity(box) == box ? value : -1; }
    public static int nullReturn(int value) { return TransportStatics.nullBox() == null ? value : -1; }
    public static int nullArgument(int value) { return TransportStatics.valueOr(null, value); }
    public static int nonnullArgument(int value) { return TransportStatics.valueOr(new TransportBox(value), -1); }
    public static int intArrayReturn(int value) { int[] values = TransportStatics.ints(value); return values[0] * 10 + values[1]; }
    public static int intArrayArgument(int value) { int[] values = new int[2]; values[0] = value; values[1] = value + 2; return TransportStatics.sum(values); }
    public static int refArrayReturn(int value) { TransportBox[] values = TransportStatics.boxes(value); return values[0].value + values[1].value; }
    public static int refArrayArgument(int value) { TransportBox[] values = new TransportBox[2]; values[0] = new TransportBox(value); values[1] = new TransportBox(value + 3); return TransportStatics.sumBoxes(values); }
    public static int crossInterfaceFactory(int value) { return OtherTransport.wrap(value).value; }
    public static int interfaceClassInterface(int value) { return OtherTransport.classHop(value); }
    public static int finalArrayElementMutation(int value) { TransportStatics.FINAL_VALUES[0] = value; return TransportStatics.FINAL_VALUES[0]; }
    public static int finalObjectElementMutation(int value) { TransportStatics.FINAL_BOX.value = value; return TransportStatics.FINAL_BOX.value; }
    public static int defaultFactory(int value) { return new TransportImpl().makeDefault(value).value; }
    public static int defaultArray(int value) { return new TransportImpl().arrayDefault(value)[1]; }
}

interface TransportStatics {
    TransportBox FINAL_BOX = make(1);
    int[] FINAL_VALUES = ints(2);
    static TransportBox make(int value) { return new TransportBox(value + 10); }
    static TransportBox identity(TransportBox value) { return value; }
    static Object objectIdentity(Object value) { return value; }
    static TransportBox nullBox() { return null; }
    static int valueOr(TransportBox value, int fallback) { return value == null ? fallback : value.value; }
    static int[] ints(int value) { int[] result = new int[2]; result[0] = value; result[1] = value + 1; return result; }
    static int sum(int[] values) { return values[0] + values[1]; }
    static TransportBox[] boxes(int value) { TransportBox[] result = new TransportBox[2]; result[0] = make(value); result[1] = make(value + 1); return result; }
    static int sumBoxes(TransportBox[] values) { return values[0].value + values[1].value; }
}
interface OtherTransport {
    static TransportBox wrap(int value) { return TransportStatics.make(value + 20); }
    static int classHop(int value) { return TransportClass.call(value); }
}
interface TransportDefault {
    default TransportBox makeDefault(int value) { return TransportStatics.make(value + 30); }
    default int[] arrayDefault(int value) { return TransportStatics.ints(value + 40); }
}
class TransportImpl implements TransportDefault {}
class TransportBox { int value; TransportBox(int value) { this.value = value; } }
class TransportClass { static int call(int value) { return OtherTransport.wrap(value).value; } }
