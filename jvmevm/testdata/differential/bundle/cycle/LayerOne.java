package bundle.cycle;

public class LayerOne {
    public static int forward(int value) {
        return LayerTwo.forward(value + 2) * 2;
    }

    public static int walk(int value, int depth) {
        int saved = value;
        if (depth == 0) {
            return saved;
        }
        return saved + LayerTwo.walk(value + 1, depth - 1);
    }
}
