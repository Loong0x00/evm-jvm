import java.util.Properties;

public final class SystemPropertyProbe {
    private static void check(boolean value) {
        if (!value) throw new AssertionError();
    }

    public static void main(String[] args) {
        check(System.getProperty("mc.system.property.absent") == null);
        check(System.getProperty("mc.system.property.absent") == null);
        boolean npe = false;
        try { System.getProperty(null); } catch (NullPointerException expected) { npe = true; }
        check(npe);
        boolean iae = false;
        try { System.getProperty(""); } catch (IllegalArgumentException expected) { iae = true; }
        check(iae);
        check(System.getSecurityManager() == null);
        int[] source = new int[] { 7, 9 };
        int[] target = new int[] { 0, 0 };
        System.arraycopy(source, 0, target, 0, 2);
        check(target[0] == 7 && target[1] == 9);
        Properties independent = new Properties();
        independent.setProperty("mc.system.property.absent", "guest-only");
        check(independent.getProperty("mc.system.property.absent").equals("guest-only"));
        check(System.getProperty("mc.system.property.absent") == null);
    }
}
