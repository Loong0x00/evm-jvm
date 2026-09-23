import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Deterministic, generated-only Java 8 raw-float oracle. */
public final class FloatFixtureGenerator {
    private static final int[] SPECIAL_BITS = {
        0x80000000, // -0.0f
        0x7fc00001, // quiet NaN payload 1
        0x7fc12345, // quiet NaN payload 2
        0xffc54321, // negative quiet NaN payload
        0x7f800000, // +infinity
        0xff800000  // -infinity
    };

    private FloatFixtureGenerator() { }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: FloatFixtureGenerator OUTPUT_DIR");
        }
        File out = new File(args[0]);
        if (!out.exists() && !out.mkdirs()) {
            throw new IOException("cannot create output directory: " + out);
        }
        if (!out.isDirectory()) {
            throw new IOException("output is not a directory: " + out);
        }

        Fixture[] fixtures = {
            fixture("float-16-small", 16, 8),
            fixture("float-1024-sparse", 1024, 32),
            fixture("float-1024-dense", 1024, 400),
            fixture("float-65536-sparse", 65536, 128),
            fixture("float-65536-dense", 65536, 30000)
        };
        for (Fixture fixture : fixtures) {
            writeFloatBits(new File(out, fixture.name + ".u32be"), fixture.values);
        }
        writeReferenceControl(new File(out, "reference-control.json"));
        writeLongControl(new File(out, "long-control.u64be"));
        writeManifest(new File(out, "oracle.json"), fixtures);
    }

    private static Fixture fixture(String name, int length, int nonzeroCount) {
        float[] values = new float[length]; // Java initializes every cell to +0.0f.
        for (int i = 0; i < SPECIAL_BITS.length; i++) {
            values[i] = Float.intBitsToFloat(SPECIAL_BITS[i]);
        }
        int count = SPECIAL_BITS.length;
        if (Float.floatToRawIntBits(values[length - 1]) == 0) {
            values[length - 1] = Float.intBitsToFloat(valueBits(count++));
        }
        for (int k = 1; count < nonzeroCount; k++) {
            int index = (int) (((long) k * (long) length) / (long) nonzeroCount);
            if (index < length && Float.floatToRawIntBits(values[index]) == 0) {
                values[index] = Float.intBitsToFloat(valueBits(count++));
            }
            if (k > length * 2) {
                throw new AssertionError("fixture fill did not converge: " + name);
            }
        }
        int actual = 0;
        for (float value : values) {
            if (Float.floatToRawIntBits(value) != 0) {
                actual++;
            }
        }
        if (actual != nonzeroCount) {
            throw new AssertionError(name + " expected " + nonzeroCount + " nonzero raw cells, got " + actual);
        }
        return new Fixture(name, values, actual);
    }

    private static int valueBits(int ordinal) {
        // Distinct, finite, nonzero binary32 values in [0.5, 1.0).
        return 0x3f000000 | (int) (((long) ordinal * 0x45d9f3bL) & 0x007fffffL);
    }

    private static void writeFloatBits(File file, float[] values) throws IOException {
        DataOutputStream data = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(file)));
        try {
            for (float value : values) {
                // Do not use writeFloat/floatToIntBits: those canonicalize NaN payloads.
                data.writeInt(Float.floatToRawIntBits(value));
            }
        } finally {
            data.close();
        }
    }

    private static void writeReferenceControl(File file) throws IOException {
        writeUtf8(file, "[\"alpha\",null,\"alpha\",\"guest\",\"\"]\n");
    }

    private static void writeLongControl(File file) throws IOException {
        long[] values = {
            0L,
            1L,
            -1L,
            Long.MIN_VALUE,
            Long.MAX_VALUE,
            0x00000001ffffffffL,
            0x7ff8000000000042L,
            0x8000000000000000L
        };
        DataOutputStream data = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(file)));
        try {
            for (long value : values) {
                data.writeLong(value);
            }
        } finally {
            data.close();
        }
    }

    private static void writeManifest(File file, Fixture[] fixtures) throws IOException {
        StringBuilder json = new StringBuilder();
        json.append("{\n  \"schema\":\"generated-java8-float-bits-v1\",\n");
        json.append("  \"floatEncoding\":\"Float.floatToRawIntBits, big-endian u32\",\n");
        json.append("  \"floatFixtures\":[\n");
        for (int i = 0; i < fixtures.length; i++) {
            Fixture fixture = fixtures[i];
            json.append("    {\"file\":\"").append(fixture.name).append(".u32be\",\"length\":")
                .append(fixture.values.length).append(",\"nonzeroRawBits\":").append(fixture.nonzeroCount)
                .append("}\n");
            if (i + 1 != fixtures.length) {
                int last = json.length() - 1;
                json.insert(last, ',');
            }
        }
        json.append("  ],\n");
        json.append("  \"referenceControl\":{\"file\":\"reference-control.json\",\"length\":5},\n");
        json.append("  \"longControl\":{\"file\":\"long-control.u64be\",\"length\":8,\"encoding\":\"big-endian u64\"}\n");
        json.append("}\n");
        writeUtf8(file, json.toString());
    }

    private static void writeUtf8(File file, String text) throws IOException {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        FileOutputStream output = new FileOutputStream(file);
        try {
            output.write(bytes);
        } finally {
            output.close();
        }
    }

    private static final class Fixture {
        final String name;
        final float[] values;
        final int nonzeroCount;

        Fixture(String name, float[] values, int nonzeroCount) {
            this.name = name;
            this.values = values;
            this.nonzeroCount = nonzeroCount;
        }
    }
}
