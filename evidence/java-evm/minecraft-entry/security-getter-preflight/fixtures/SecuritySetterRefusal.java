/** TEST-only explicit unsupported-member refusal control. */
public final class SecuritySetterRefusal {
    public static void main(String[] ignored) {
        // The candidate intentionally has no setter/security framework.
        System.setSecurityManager(null);
    }
}
