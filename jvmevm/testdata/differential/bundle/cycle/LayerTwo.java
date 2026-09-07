package bundle.cycle;

public class LayerTwo {
    public static int forward(int value) {
        return LayerThree.forward(value * 3) - 5;
    }

    public static int walk(int value, int depth) {
        int saved = value * 2;
        if (depth == 0) {
            return saved;
        }
        return saved + LayerThree.walk(value + 1, depth - 1);
    }
}
