package bundle.m5a.dispatch;

/** Narrow descriptors across static, special, virtual, interface, default, bridge, and constructor calls. */
public class DispatchRoot {
    private static byte staticByte(byte value) { return (byte) (value + 129); }
    private static short staticShort(short value) { return (short) (value * 257); }
    private static char staticChar(char value) { return (char) (value + 65535); }
    private static boolean staticBoolean(boolean value) { return !value; }

    private byte privateByte(byte value) { return (byte) (value - 2); }
    private boolean privateBoolean(boolean value) { return !value; }

    public static int staticByteCall(int value) { return staticByte((byte) value); }
    public static int staticShortCall(int value) { return staticShort((short) value); }
    public static int staticCharCall(int value) { return staticChar((char) value); }
    public static int staticBooleanCall(int value) { return staticBoolean((value & 1) != 0) ? 1 : 0; }
    public static int privateSpecialByte(int value) { return new DispatchRoot().privateByte((byte) value); }
    public static int privateSpecialBoolean(int value) { return new DispatchRoot().privateBoolean((value & 1) != 0) ? 1 : 0; }

    public static int constructorArguments(int value) {
        DispatchConstructed made = new DispatchConstructed((byte) value, (short) (value * 257),
            (char) (value - 1), (value & 1) != 0);
        return made.pack();
    }

    public static int constructorChain(int value) {
        DispatchConstructedChild made = new DispatchConstructedChild((byte) value, (char) (value + 65535));
        return made.packChild();
    }

    private static byte virtualByteSite(DispatchBase receiver, byte value) { return receiver.byteValue(value); }
    private static short virtualShortSite(DispatchBase receiver, short value) { return receiver.shortValue(value); }
    private static char interfaceCharSite(DispatchFace receiver, char value) { return receiver.charValue(value); }
    private static boolean interfaceBooleanSite(DispatchFace receiver, boolean value) { return receiver.booleanValue(value); }
    private static byte interfaceDefaultSite(DispatchFace receiver, byte value) { return receiver.defaultByte(value); }

    public static int virtualBaseByte(int value) { return virtualByteSite(new DispatchBase(), (byte) value); }
    public static int virtualOverrideByte(int value) { return virtualByteSite(new DispatchOverride(), (byte) value); }
    public static int virtualOverrideShort(int value) { return virtualShortSite(new DispatchOverride(), (short) value); }
    public static int interfaceBaseChar(int value) { return interfaceCharSite(new DispatchBase(), (char) value); }
    public static int interfaceOverrideChar(int value) { return interfaceCharSite(new DispatchOverride(), (char) value); }
    public static int interfaceBoolean(int value) { return interfaceBooleanSite(new DispatchOverride(), (value & 1) != 0) ? 1 : 0; }
    public static int defaultByte(int value) { return new DispatchBase().defaultByte((byte) value); }
    public static int defaultBoolean(int value) { return new DispatchBase().defaultBoolean((value & 1) != 0) ? 1 : 0; }
    public static int interfaceDefaultByte(int value) { return interfaceDefaultSite(new DispatchBase(), (byte) value); }
    public static int directInterfaceSuper(int value) { return new DispatchBase().directDefault((byte) value); }
    public static int interfaceStaticShort(int value) { return DispatchFace.staticShort((short) value); }
    public static int bridgeInterface(int value) { return bridgeInterfaceSite(new DispatchFactory(), value).b; }
    public static int bridgeVirtual(int value) { return bridgeVirtualSite(new DispatchBridgeChild(), value).b; }

    private static DispatchValue bridgeInterfaceSite(DispatchFactoryFace factory, int value) { return factory.make(value); }
    private static DispatchValue bridgeVirtualSite(DispatchBridgeBase factory, int value) { return factory.make(value); }

    public static int mixedCallModes(int value) {
        byte first = staticByte((byte) value);
        byte second = virtualByteSite(new DispatchOverride(), first);
        char third = interfaceCharSite(new DispatchBase(), (char) second);
        return third + DispatchFace.staticShort((short) second);
    }
}

interface DispatchFace {
    char charValue(char value);
    boolean booleanValue(boolean value);
    default byte defaultByte(byte value) { return (byte) (value + 3); }
    default boolean defaultBoolean(boolean value) { return !value; }
    static short staticShort(short value) { return (short) (value - 32769); }
}

class DispatchBase implements DispatchFace {
    public byte byteValue(byte value) { return (byte) (value + 1); }
    byte directDefault(byte value) { return DispatchFace.super.defaultByte(value); }
    public short shortValue(short value) { return (short) (value + 2); }
    public char charValue(char value) { return (char) (value + 3); }
    public boolean booleanValue(boolean value) { return value; }
}
class DispatchOverride extends DispatchBase {
    public byte byteValue(byte value) { return (byte) (value + 4); }
    public short shortValue(short value) { return (short) (value + 5); }
    public char charValue(char value) { return (char) (value + 6); }
    public boolean booleanValue(boolean value) { return !value; }
}

class DispatchConstructed {
    byte b;
    short s;
    char c;
    boolean z;
    DispatchConstructed(byte b, short s, char c, boolean z) { this.b = b; this.s = s; this.c = c; this.z = z; }
    int pack() { return b * 1000000 + s * 10 + c + (z ? 1 : 0); }
}
class DispatchConstructedChild extends DispatchConstructed {
    char own;
    DispatchConstructedChild(byte value, char own) { this((short) (value * 257), value, own); }
    DispatchConstructedChild(short expanded, byte value, char own) { super(value, expanded, own, (value & 1) != 0); this.own = own; }
    int packChild() { return pack() + own; }
}

class DispatchValue { byte b; DispatchValue(byte b) { this.b = b; } }
class DispatchChildValue extends DispatchValue { DispatchChildValue(byte b) { super(b); } }
interface DispatchFactoryFace { DispatchValue make(int value); }
class DispatchFactory implements DispatchFactoryFace {
    public DispatchChildValue make(int value) { return new DispatchChildValue((byte) value); }
}
class DispatchBridgeBase { DispatchValue make(int value) { return new DispatchValue((byte) (value + 1)); } }
class DispatchBridgeChild extends DispatchBridgeBase {
    DispatchChildValue make(int value) { return new DispatchChildValue((byte) (value + 2)); }
}
