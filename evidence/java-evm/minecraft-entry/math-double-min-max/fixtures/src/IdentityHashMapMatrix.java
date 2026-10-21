import java.io.Serializable;
import java.util.AbstractMap;
import java.util.IdentityHashMap;
import java.util.Map;

public final class IdentityHashMapMatrix {
    private static void check(IdentityHashMap map) {
        if (map.size() != 0 || !map.isEmpty()) throw new AssertionError("empty state");
        if (!(map instanceof AbstractMap)) throw new AssertionError("AbstractMap");
        if (!(map instanceof Map)) throw new AssertionError("Map");
        if (!(map instanceof Cloneable)) throw new AssertionError("Cloneable");
        if (!(map instanceof Serializable)) throw new AssertionError("Serializable");
        if (map.getClass() != IdentityHashMap.class) throw new AssertionError("class mirror");
    }

    public static void main(String[] args) {
        IdentityHashMap zero = new IdentityHashMap(0);
        IdentityHashMap one = new IdentityHashMap(1);
        IdentityHashMap two = new IdentityHashMap(2);
        IdentityHashMap three = new IdentityHashMap(3);
        IdentityHashMap ten = new IdentityHashMap(10);
        IdentityHashMap twentyOne = new IdentityHashMap(21);
        IdentityHashMap fiveTwelve = new IdentityHashMap(512);
        IdentityHashMap oneK = new IdentityHashMap(1024);
        IdentityHashMap maximumLegalTable = new IdentityHashMap(21845);
        check(zero);
        check(one);
        check(two);
        check(three);
        check(ten);
        check(twentyOne);
        check(fiveTwelve);
        check(oneK);
        check(maximumLegalTable);
        IdentityHashMap[] all = {
            zero, one, two, three, ten, twentyOne, fiveTwelve, oneK, maximumLegalTable
        };
        for (int i = 0; i < all.length; i++) {
            for (int j = i + 1; j < all.length; j++) {
                if (all[i] == all[j]) throw new AssertionError("object identity");
            }
        }
        Object objectView = fiveTwelve;
        Map interfaceView = oneK;
        if (objectView.getClass() != interfaceView.getClass()) {
            throw new AssertionError("canonical mirror identity");
        }
    }
}
