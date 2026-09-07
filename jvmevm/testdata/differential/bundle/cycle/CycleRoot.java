package bundle.cycle;

public class CycleRoot {
    public static int nestedChain(int value) {
        return LayerOne.forward(value);
    }

    public static int cyclicWalk(int value, int depth) {
        return LayerOne.walk(value, depth);
    }

    public static int cyclicCallerPrefix(int prefix, int value, int depth) {
        int saved = prefix;
        int walked = LayerTwo.walk(value, depth);
        return saved * 100 + walked;
    }
}
