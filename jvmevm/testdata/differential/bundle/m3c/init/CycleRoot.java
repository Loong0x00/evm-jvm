package bundle.m3c.init;

public class CycleRoot {
    public static int firstUseA(int addend) {
        int first = CycleA.value;
        return first * 100 + CycleB.value + addend;
    }

    public static int firstUseB(int addend) {
        int first = CycleB.value;
        return CycleA.value * 100 + first + addend;
    }
}
