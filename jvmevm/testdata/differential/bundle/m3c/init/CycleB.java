package bundle.m3c.init;

public class CycleB {
    static int value = CycleA.read() + 2;

    static int read() {
        return value;
    }
}
