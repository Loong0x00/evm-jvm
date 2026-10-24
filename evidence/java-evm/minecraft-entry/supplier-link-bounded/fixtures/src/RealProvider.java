package fixture;

public final class RealProvider implements ProviderLink {
    public static String token = "supplier-token";
    public static int calls;
    public static boolean fail;

    public String get() {
        calls++;
        if (fail) return token.substring(0, 1 / 0);
        return token;
    }
}
