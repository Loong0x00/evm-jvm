package bundle.m3c.init;

public class CycleA {
    static int value = CycleB.read() + 1;

    static int read() {
        return value;
    }
}
