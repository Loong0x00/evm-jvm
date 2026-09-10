import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;

public final class VFS0aErrors {
    public static int nullFileArg() {
        int caught = 0;
        try {
            new FileInputStream((File)null);
        } catch (NullPointerException expected) {
            caught++;
        } catch (FileNotFoundException wrong) {
            return 0;
        }
        try {
            new FileOutputStream((File)null);
        } catch (NullPointerException expected) {
            caught++;
        } catch (FileNotFoundException wrong) {
            return 0;
        }
        return caught == 2 ? 1 : 0;
    }

    public static int missingInputMessage() {
        try {
            new FileInputStream(new File("missing//input/"));
            return 0;
        } catch (FileNotFoundException expected) {
            return "missing/input (No such file or directory)".equals(expected.getMessage()) ? 1 : 0;
        }
    }

    public static int missingOutputParentMessage() {
        try {
            new FileOutputStream(new File("missing//parent/file"));
            return 0;
        } catch (FileNotFoundException expected) {
            return "missing/parent/file (No such file or directory)".equals(expected.getMessage()) ? 1 : 0;
        }
    }

    public static int directoryOpenMessage() {
        try {
            new FileInputStream(new File("directory"));
            return 0;
        } catch (FileNotFoundException expected) {
            return "directory (Is a directory)".equals(expected.getMessage()) ? 1 : 0;
        }
    }

    public static int readOnlyOutputMessage() {
        try {
            new FileOutputStream(new File("readonly"));
            return 0;
        } catch (FileNotFoundException expected) {
            return "readonly (Permission denied)".equals(expected.getMessage()) ? 1 : 0;
        }
    }

    public static int nullArrayBeforeClosed() throws IOException {
        FileInputStream input = new FileInputStream(new File("precedence"));
        input.close();
        try {
            input.read((byte[])null, 0, 1);
            return 0;
        } catch (NullPointerException expected) {
            return 1;
        } catch (IOException wrong) {
            return 0;
        }
    }

    public static int boundsBeforeClosed() throws IOException {
        FileOutputStream output = new FileOutputStream(new File("bounds"));
        output.close();
        try {
            output.write(new byte[1], 2, 1);
            return 0;
        } catch (IndexOutOfBoundsException expected) {
            return 1;
        } catch (IOException wrong) {
            return 0;
        }
    }

    public static int zeroLengthClosed() throws IOException {
        FileInputStream input = new FileInputStream(new File("zero"));
        input.close();
        byte[] value = new byte[1];
        int read = input.read(value, 1, 0);
        FileOutputStream output = new FileOutputStream(new File("zero-out"));
        output.close();
        output.write(value, 1, 0);
        return read == 0 ? 1 : 0;
    }
}
