package bundle.m5da.transport;

/** Captured VM exception references through supported reference transports. */
public final class TransportRoot {
    private static Throwable staticValue;
    private Throwable instanceValue;

    private static void fault() { int ignored = 1 / 0; }
    private static Throwable capture() {
        try { fault(); return null; } catch (ArithmeticException e) { return e; }
    }
    private static Throwable bounce(Throwable value) { return value; }
    private static void throwIt(Throwable value) throws Throwable { throw value; }

    public static int localIdentity(int seed) {
        Throwable value = capture();
        try { throwIt(value); return -1; } catch (Throwable caught) { return caught == value ? seed + 401 : -2; }
    }
    public static int staticFieldIdentity(int seed) {
        staticValue = capture();
        try { throwIt(staticValue); return -1; } catch (Throwable caught) { return caught == staticValue ? seed + 402 : -2; }
    }
    public static int instanceFieldIdentity(int seed) {
        TransportRoot box = new TransportRoot();
        box.instanceValue = capture();
        try { throwIt(box.instanceValue); return -1; } catch (Throwable caught) { return caught == box.instanceValue ? seed + 403 : -2; }
    }
    public static int throwableArrayIdentity(int seed) {
        Throwable value = capture();
        Throwable[] values = new Throwable[2];
        values[1] = value;
        try { throwIt(values[1]); return -1; } catch (Throwable caught) { return caught == value ? seed + 404 : -2; }
    }
    public static int objectArrayCastIdentity(int seed) {
        Throwable value = capture();
        Object[] values = new Object[] { value };
        Throwable cast = (Throwable) values[0];
        try { throwIt(cast); return -1; } catch (Throwable caught) { return caught == value ? seed + 405 : -2; }
    }
    public static int argumentReturnIdentity(int seed) {
        Throwable value = capture();
        Throwable returned = bounce(value);
        try { throwIt(returned); return -1; } catch (Throwable caught) { return caught == value ? seed + 406 : -2; }
    }
    public static int runtimeCastIdentity(int seed) {
        Throwable value = capture();
        Object object = value;
        RuntimeException cast = (RuntimeException) object;
        try { throw cast; } catch (Throwable caught) { return caught == value ? seed + 407 : -2; }
    }
    public static int arithmeticCastIdentity(int seed) {
        Throwable value = capture();
        Object object = value;
        ArithmeticException cast = (ArithmeticException) object;
        try { throw cast; } catch (Throwable caught) { return caught == value ? seed + 408 : -2; }
    }
    public static int aliasesIdentity(int seed) {
        Throwable first = capture();
        Throwable second = first;
        Throwable third = bounce(second);
        return first == second && second == third ? seed + 409 : -1;
    }
    public static int distinctFresh(int seed) {
        Throwable first = capture();
        Throwable second = capture();
        return first != second ? seed + 410 : -1;
    }
    public static int threeFresh(int seed) {
        Throwable first = capture();
        Throwable second = capture();
        Throwable third = capture();
        return first != second && first != third && second != third ? seed + 411 : -1;
    }
    public static int rethrowNoFresh(int seed) {
        Throwable value = capture();
        Throwable first;
        try { throw value; } catch (Throwable caught) { first = caught; }
        try { throw first; } catch (Throwable caught) { return caught == value ? seed + 412 : -1; }
    }
    public static int nullAthrowExact(int seed) throws Throwable {
        Throwable value = null;
        try { throw value; } catch (NullPointerException caught) { return seed + 413; }
    }
    public static int nullAthrowFresh(int seed) throws Throwable {
        Throwable first;
        try { throw (Throwable) null; } catch (NullPointerException caught) { first = caught; }
        try { throw (Throwable) null; } catch (NullPointerException caught) { return caught != first ? seed + 414 : -1; }
    }
}
