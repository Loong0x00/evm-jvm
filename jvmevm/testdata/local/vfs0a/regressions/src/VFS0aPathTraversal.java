import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;

/** Focused stock-Java path traversal expectations found after the 24-root freeze. */
public final class VFS0aPathTraversal {
    private static boolean inputMessage(String path, String expected) {
        File file = new File(path);
        if (file.exists()) return false;
        try {
            new FileInputStream(file);
            return false;
        } catch (FileNotFoundException failure) {
            return expected.equals(failure.getMessage());
        }
    }

    private static boolean outputMessage(String path, String expected) {
        File file = new File(path);
        if (file.exists()) return false;
        try {
            new FileOutputStream(file);
            return false;
        } catch (FileNotFoundException failure) {
            return expected.equals(failure.getMessage());
        }
    }

    public static int fileChildInput() {
        return inputMessage("file/child", "file/child (Not a directory)") ? 1 : 0;
    }

    public static int missingDotDotInput() {
        return inputMessage("missing/../seed", "missing/../seed (No such file or directory)") ? 1 : 0;
    }

    public static int fileDotDotInput() {
        return inputMessage("file/../seed", "file/../seed (Not a directory)") ? 1 : 0;
    }

    public static int fileChildOutput() {
        return outputMessage("file/child", "file/child (Not a directory)") ? 1 : 0;
    }

    public static int missingDotDotOutput() {
        return outputMessage("missing/../new", "missing/../new (No such file or directory)") ? 1 : 0;
    }

    public static int fileDotDotOutput() {
        return outputMessage("file/../new", "file/../new (Not a directory)") ? 1 : 0;
    }

    public static int mkdirTraversal() {
        boolean first = !new File("missing/../one").mkdir();
        boolean second = !new File("file/../two").mkdir();
        boolean third = new File("missing/../many-a").mkdirs();
        boolean fourth = new File("file/../many-b").mkdirs();
        return first && second && third && fourth ? 1 : 0;
    }
}
