package java.io;
public class FileOutputStream extends OutputStream {
    private int handle;

    public FileOutputStream(File file) throws FileNotFoundException {
        this(file, false);
    }

    public FileOutputStream(File file, boolean append) throws FileNotFoundException {
        super();
        if (file == null) throw new NullPointerException();
        int status = open0(file, append);
        if (status > 0) {
            handle = status;
            return;
        }
        throw new FileNotFoundException(errorMessage(file, status));
    }

    public void write(int value) throws IOException {
        int status = writeOne0(value);
        if (status == -2) throw new IOException("Stream Closed");
    }

    public void write(byte[] value) throws IOException {
        write(value, 0, value.length);
    }

    public void write(byte[] value, int offset, int length) throws IOException {
        int size = value.length;
        if (offset < 0 || length < 0 || offset > size - length)
            throw new IndexOutOfBoundsException();
        if (length == 0) return;
        int status = write0(value, offset, length);
        if (status == -2) throw new IOException("Stream Closed");
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

    private native int open0(File file, boolean append);
    private native int writeOne0(int value);
    private native int write0(byte[] value, int offset, int length);
    private native int close0();
}
