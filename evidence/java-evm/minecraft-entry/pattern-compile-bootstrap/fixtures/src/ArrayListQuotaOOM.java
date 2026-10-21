import java.util.ArrayList;
public final class ArrayListQuotaOOM {
    public static void main(String[] args) { new ArrayList(65537); }
}
