import java.io.File;

public final class VFS0aPaths {
    public static int existsMissing() {
        File value = new File("missing");
        return !value.exists() && !value.isFile() && !value.isDirectory() ? 1 : 0;
    }

    public static int seedFile() {
        File value = new File("seed.bin");
        return value.exists() && value.isFile() && !value.isDirectory() ? 1 : 0;
    }

    public static int seedDirectory() {
        File value = new File("seed-dir");
        File leaf = new File("seed-dir/leaf");
        return value.exists() && value.isDirectory() && leaf.isFile() ? 1 : 0;
    }

    public static int mkdirOnce() {
        File value = new File("once");
        boolean first = value.mkdir();
        boolean second = value.mkdir();
        return first && !second && value.exists() && value.isDirectory() ? 1 : 0;
    }

    public static int mkdirsNested() {
        File value = new File("deep//one///two/");
        boolean first = value.mkdirs();
        boolean second = value.mkdirs();
        File normalized = new File("deep/one/two");
        return first && !second && normalized.isDirectory() && value.compareTo(normalized) == 0 ? 1 : 0;
    }

    public static int readonlyMkdir() {
        File locked = new File("locked");
        File child = new File("locked/child");
        return locked.isFile() && !child.mkdir() && !child.mkdirs() && !child.exists() ? 1 : 0;
    }

    public static int lexicalAlias() {
        File parent = new File("alias/base");
        if (!parent.mkdirs()) return 0;
        File gone = new File("alias/base/gone");
        if (!gone.mkdir()) return 0;
        File lexical = new File("alias/base/./gone/../child");
        if (!lexical.mkdir()) return 0;
        File canonical = new File("alias/base/child");
        return lexical.exists() && canonical.isDirectory() && lexical.compareTo(canonical) != 0 ? 1 : 0;
    }

    public static int comparablePaths() {
        File normalizedA = new File("same//path/");
        File normalizedB = new File("same/path");
        File upper = new File("Same/path");
        Comparable<File> comparable = normalizedA;
        return comparable.compareTo(normalizedB) == 0 && upper.compareTo(normalizedA) < 0 ? 1 : 0;
    }
}
