import java.lang.reflect.Field;

/** Host oracle for the checked-in generated PackedFloatMain fixture only. */
public final class RawFloatOracle {
    public static void main(String[] args) throws Exception {
        Class<?> main = Class.forName("PackedFloatMain");
        main.getMethod("main", String[].class).invoke(null, (Object) new String[0]);
        Field field = main.getDeclaredField("values");
        field.setAccessible(true);
        float[] values = (float[]) field.get(null);
        for (float value : values) {
            System.out.printf("%08x%n", Float.floatToRawIntBits(value));
        }
    }
}
