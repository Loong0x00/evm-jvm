package bundle.m5a.dispatch;

/** A public interface remains a valid I-only root while calling narrow interface statics internally. */
public interface PublicDispatch {
    static byte narrowByte(int value) { return (byte) (value + 255); }
    static char narrowChar(int value) { return (char) (value - 1); }
    static boolean lowBitSource(int value) { return (value & 1) != 0; }

    static int interfaceRootByte(int value) { return narrowByte(value); }
    static int interfaceRootChar(int value) { return narrowChar(value); }
    static int interfaceRootBoolean(int value) { return lowBitSource(value) ? 1 : 0; }
}
