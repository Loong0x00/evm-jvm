import java.io.Serializable;
import java.util.AbstractMap;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.lang.reflect.Array;

/** Generated Java 8 fixture: exercises only EnumMap type linkage, never an EnumMap instance. */
public final class EnumMapTypeLinkProbe {
    private EnumMapTypeLinkProbe() {}

    private static void require(boolean ok) {
        if (!ok) throw new RuntimeException();
    }

    public static void main(String[] args) {
        require(EnumMap.class == EnumMap.class);
        require("java.util.EnumMap".equals(EnumMap.class.getName()));
        Map map = new LinkedHashMap();
        Object wrong = map;
        require(!(wrong instanceof EnumMap));
        require(!(null instanceof EnumMap));
        try {
            EnumMap ignored = (EnumMap) wrong;
            throw new RuntimeException();
        } catch (ClassCastException expected) {
            // Ordinary guest cast failure.
        }
        require((EnumMap) null == null);

        EnumMap[] zero = new EnumMap[0];
        EnumMap[] one = new EnumMap[1];
        Object[] objects = one;
        Map[] maps = one;
        AbstractMap[] abstractMaps = one;
        Serializable[] serializables = one;
        Cloneable[] cloneables = one;
        require(objects == one && maps == one && abstractMaps == one);
        require(serializables == one && cloneables == one);
        require(zero.length == 0 && one.length == 1);
        require((Object) one instanceof Map[]);
        require((Object) one instanceof AbstractMap[]);
        require((Object) one instanceof Serializable[]);
        require((Object) one instanceof Cloneable[]);
        require(one.clone() != one);
        require(((EnumMap[]) one.clone()).length == 1);
        try {
            objects[0] = wrong;
            throw new RuntimeException();
        } catch (ArrayStoreException expected) {
            // Actual component assignability rejects LinkedHashMap.
        }

        Object reflected = Array.newInstance(EnumMap.class, 2);
        require(reflected instanceof EnumMap[]);
        require(((EnumMap[]) reflected).length == 2);
    }
}
