// HOST TEST ONLY, excluded from the ZIP and never called by the EVM driver.
public class Oracle {
    public static void main(String[] args) {
        try { System.out.println("R:" + CastEntry.run(Integer.parseInt(args[0]))); }
        catch (Throwable t) { System.out.println("X:" + t.getClass().getName()); }
    }
}
