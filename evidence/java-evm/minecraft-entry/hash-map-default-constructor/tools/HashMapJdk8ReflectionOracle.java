import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.HashMap;
import java.util.Map;

/** Read-only oracle for the local JDK 8 java.util.HashMap default constructor. */
public final class HashMapJdk8ReflectionOracle {
    private static String describe(Field field, Object map) throws Exception {
        field.setAccessible(true);
        Object value = Modifier.isStatic(field.getModifiers()) ? field.get(null) : field.get(map);
        String rendered;
        if (value == null) rendered = "null";
        else if (value instanceof Float) rendered = "0x" + Integer.toHexString(Float.floatToRawIntBits((Float) value));
        else rendered = String.valueOf(value);
        return field.getName() + "|" + field.getType().getName() + "|" + Modifier.toString(field.getModifiers()) + "|" + rendered;
    }

    public static void main(String[] args) throws Exception {
        HashMap<Object, Object> map = new HashMap<Object, Object>();
        System.out.println("java.version=" + System.getProperty("java.version"));
        System.out.println("class=" + HashMap.class.getName());
        System.out.println("super=" + HashMap.class.getSuperclass().getName());
        for (Class<?> iface : HashMap.class.getInterfaces()) System.out.println("interface=" + iface.getName());
        for (Field field : HashMap.class.getDeclaredFields()) System.out.println("field=" + describe(field, map));
        System.out.println("size=" + map.size());
        System.out.println("isEmpty=" + map.isEmpty());
        Field table = HashMap.class.getDeclaredField("table");
        table.setAccessible(true);
        System.out.println("tableIsNull=" + (table.get(map) == null));
        Field entrySet = HashMap.class.getDeclaredField("entrySet");
        entrySet.setAccessible(true);
        System.out.println("entrySetIsNull=" + (entrySet.get(map) == null));
        Field size = HashMap.class.getDeclaredField("size");
        size.setAccessible(true);
        System.out.println("sizeField=" + size.getInt(map));
        Field modCount = HashMap.class.getDeclaredField("modCount");
        modCount.setAccessible(true);
        System.out.println("modCount=" + modCount.getInt(map));
        Field threshold = HashMap.class.getDeclaredField("threshold");
        threshold.setAccessible(true);
        System.out.println("threshold=" + threshold.getInt(map));
        Field loadFactor = HashMap.class.getDeclaredField("loadFactor");
        loadFactor.setAccessible(true);
        float factor = loadFactor.getFloat(map);
        System.out.println("loadFactorBits=0x" + Integer.toHexString(Float.floatToRawIntBits(factor)));
        System.out.println("loadFactor=" + factor);
        System.out.println("defaultCtorCount=" + HashMap.class.getDeclaredConstructors().length);
        System.out.println("containsMap=" + (map instanceof Map));
        System.out.println("containsCloneable=" + (map instanceof Cloneable));
        System.out.println("containsSerializable=" + (map instanceof java.io.Serializable));
        System.out.println("mapInterfaceCount=" + HashMap.class.getInterfaces().length);
    }
}
