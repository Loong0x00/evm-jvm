import java.util.LinkedHashMap;
import java.util.Set;

public final class ViewEqualsRefusalProbe {
    public static void main(String[] args) {
        LinkedHashMap<Object, Object> left = new LinkedHashMap<Object, Object>();
        LinkedHashMap<Object, Object> right = new LinkedHashMap<Object, Object>();
        Set<?> leftView = left.entrySet();
        Set<?> rightView = right.entrySet();
        leftView.equals(rightView);
    }
}
