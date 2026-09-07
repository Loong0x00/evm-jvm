package bundle.cycle;

public class LayerThree {
    public static int forward(int value) {
        return value - 7;
    }

    public static int walk(int value, int depth) {
        int saved = value * 3;
        if (depth == 0) {
            return saved;
        }
        return saved + LayerOne.walk(value + 1, depth - 1);
    }
}
