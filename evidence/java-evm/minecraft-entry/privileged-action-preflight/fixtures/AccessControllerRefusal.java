import java.security.AccessController;
/** TEST-only unsupported API control: no AccessController bootstrap is supplied. */
public final class AccessControllerRefusal {
    public static void main(String[] ignored) { AccessController.getContext(); }
}
