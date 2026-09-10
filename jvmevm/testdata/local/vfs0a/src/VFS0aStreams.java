import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

public final class VFS0aStreams {
    public static int readSingleEOF() throws IOException {
        FileInputStream input = new FileInputStream(new File("single"));
        int first = input.read();
        int eof = input.read();
        input.close();
        return first == 65 && eof == -1 ? 1 : 0;
    }

    public static int readBulkSlice() throws IOException {
        FileInputStream input = new FileInputStream(new File("bulk"));
        byte[] value = new byte[] { 9, 9, 9, 9, 9 };
        int count = input.read(value, 1, 3);
        int eof = input.read(value, 0, 2);
        input.close();
        return count == 3 && eof == -1 && value[0] == 9 && value[1] == 65 &&
               value[2] == 66 && value[3] == 67 && value[4] == 9 ? 1 : 0;
    }

    public static int createRoundtrip() throws IOException {
        File file = new File("created");
        FileOutputStream output = new FileOutputStream(file);
        output.write(65);
        output.write(new byte[] { 66, 67, 68 }, 1, 2);
        output.close();
        FileInputStream input = new FileInputStream(file);
        byte[] value = new byte[3];
        int count = input.read(value);
        int eof = input.read();
        input.close();
        return count == 3 && eof == -1 && value[0] == 65 && value[1] == 67 && value[2] == 68 ? 1 : 0;
    }

    public static int truncate() throws IOException {
        File file = new File("truncate");
        FileOutputStream output = new FileOutputStream(file);
        output.write(new byte[] { 88, 89 });
        output.close();
        FileInputStream input = new FileInputStream(file);
        byte[] value = new byte[4];
        int count = input.read(value);
        int eof = input.read();
        input.close();
        return count == 2 && eof == -1 && value[0] == 88 && value[1] == 89 ? 1 : 0;
    }

    public static int append() throws IOException {
        File file = new File("append");
        FileOutputStream output = new FileOutputStream(file, true);
        output.write(67);
        output.write(new byte[] { 68, 69 });
        output.close();
        FileInputStream input = new FileInputStream(file);
        byte[] value = new byte[6];
        int count = input.read(value);
        input.close();
        return count == 5 && value[0] == 65 && value[1] == 66 && value[2] == 67 &&
               value[3] == 68 && value[4] == 69 ? 1 : 0;
    }

    public static int twoWriterGap() throws IOException {
        File file = new File("writers");
        FileOutputStream first = new FileOutputStream(file);
        first.write(new byte[] { 65, 66, 67 });
        FileOutputStream second = new FileOutputStream(file);
        second.write(88);
        first.write(89);
        first.close();
        second.close();
        FileInputStream input = new FileInputStream(file);
        byte[] value = new byte[5];
        int count = input.read(value);
        input.close();
        return count == 4 && value[0] == 88 && value[1] == 0 && value[2] == 0 && value[3] == 89 ? 1 : 0;
    }

    public static int staleReadCursor() throws IOException {
        File file = new File("stale");
        FileInputStream stale = new FileInputStream(file);
        byte[] first = new byte[4];
        if (stale.read(first) != 4) return 0;
        FileOutputStream truncate = new FileOutputStream(file);
        truncate.write(new byte[] { 88, 89 });
        if (stale.read() != -1) return 0;
        FileOutputStream append = new FileOutputStream(file, true);
        append.write(90);
        if (stale.read() != -1) return 0;
        truncate.close();
        append.close();
        stale.close();
        FileInputStream check = new FileInputStream(file);
        byte[] value = new byte[4];
        int count = check.read(value);
        check.close();
        return count == 3 && value[0] == 88 && value[1] == 89 && value[2] == 90 ? 1 : 0;
    }

    public static int closeTwice() throws IOException {
        FileInputStream input = new FileInputStream(new File("close"));
        input.close();
        input.close();
        try {
            input.read();
            return 0;
        } catch (IOException expected) {
            return "Stream Closed".equals(expected.getMessage()) ? 1 : 0;
        }
    }
}
