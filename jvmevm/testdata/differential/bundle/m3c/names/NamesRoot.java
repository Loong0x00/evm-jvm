package bundle.m3c.names;

public class NamesRoot {
    public static int readBoth(int prefix) {
        return prefix * 10000 + NamedA.value * 100 + NamedB.value;
    }

    public static int mutateIndependently(int first, int second) {
        NamedA.value = first;
        NamedB.value = second;
        NamedA.value++;
        NamedB.value += 2;
        return NamedA.value * 1000 + NamedB.value;
    }

    public static int alternatingCacheProbe(int delta) {
        int result = NamedA.value + NamedB.value;
        NamedA.value += delta;
        result += NamedB.value;
        NamedB.value -= delta;
        return result + NamedA.value * 10 + NamedB.value;
    }
}
