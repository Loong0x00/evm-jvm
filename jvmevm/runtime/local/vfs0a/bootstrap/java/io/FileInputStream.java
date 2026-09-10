package java.io;
public class FileInputStream extends InputStream {
    private int handle;

    public FileInputStream(File file) throws FileNotFoundException {
        super();
        if (file == null) throw new NullPointerException();
        int status = open0(file);
        if (status > 0) {
            handle = status;
            return;
        }
        throw new FileNotFoundException(errorMessage(file, status));
    }

    public int read() throws IOException {
        int status = readOne0();
        if (status == -2) throw new IOException("Stream Closed");
        return status;
    }

    public int read(byte[] value) throws IOException {
        return read(value, 0, value.length);
    }

    public int read(byte[] value, int offset, int length) throws IOException {
        int size = value.length;
        if (offset < 0 || length < 0 || offset > size - length)
            throw new IndexOutOfBoundsException();
        if (length == 0) return 0;
        int status = read0(value, offset, length);
        if (status == -2) throw new IOException("Stream Closed");
        return status;
    }

    public void close() throws IOException {
        int status = close0();
        if (status != 0) throw new IOException("Stream Closed");
    }

    private static String errorMessage(File file, int status) {
        String suffix;
        if (status == -1) suffix = " (No such file or directory)";
        else if (status == -2) suffix = " (Is a directory)";
        else if (status == -4) suffix = " (Not a directory)";
        else suffix = " (Permission denied)";
        String path = file.path0();
        int first = path.length();
        int second = suffix.length();
        char[] message = new char[first + second];
        int i = 0;
        for (; i < first; i++) message[i] = path.charAt(i);
        for (int j = 0; j < second; j++) message[i + j] = suffix.charAt(j);
        return new String(message);
    }

    private native int open0(File file);
    private native int readOne0();
    private native int read0(byte[] value, int offset, int length);
    private native int close0();
}
