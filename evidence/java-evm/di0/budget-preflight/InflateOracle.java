// HOST TEST ORACLE ONLY. Runs exclusively on parent-generated fixtures, not server code.
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public class InflateOracle {
  static String quote(String s) { return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\""; }
  static int consume(InputStream in) throws IOException {
    byte[] b=new byte[4096];int n,total=0;
    while ((n=in.read(b))!=-1) { total+=n; if(total>262144)throw new IOException("test output limit"); }
    return total;
  }
  public static void main(String[] args) throws Exception {
    Path dir=Paths.get(args[0]);List<Path> files=new ArrayList<Path>();
    try(DirectoryStream<Path> ds=Files.newDirectoryStream(dir,"*.deflate")){for(Path p:ds)files.add(p);}
    Collections.sort(files);
    System.out.println("{\"javaVersion\":"+quote(System.getProperty("java.version"))+",\"fixtures\":[");
    boolean first=true;
    for(Path p:files) {
      if(!first)System.out.println(",");first=false;
      String name=p.getFileName().toString().replace(".deflate","");byte[] raw=Files.readAllBytes(p);
      Inflater inf=new Inflater(true);inf.setInput(raw);String error="";int total=0;byte[] buf=new byte[4096];
      try { while(!inf.finished()) {int n=inf.inflate(buf);total+=n;if(total>262144)throw new IOException("test output limit");if(n==0&&!inf.finished()){if(inf.needsInput())throw new EOFException("input exhausted");if(inf.needsDictionary())throw new IOException("dictionary needed");throw new IOException("no progress");}} }
      catch(Exception e){error=e.getClass().getSimpleName()+": "+e.getMessage();}
      int remaining=inf.getRemaining();boolean finished=inf.finished();inf.end();
      String zipError="", streamError="";int zipBytes=0,streamBytes=0;
      try(ZipFile z=new ZipFile(dir.resolve("compat.zip").toFile());InputStream in=z.getInputStream(z.getEntry(name))) {zipBytes=consume(in);}catch(Exception e){zipError=e.getClass().getSimpleName()+": "+e.getMessage();}
      // A separate one-entry ZIP preserves this fixture's original encoded bytes;
      // no host inflate/re-encode is used to prepare it.
      try(ZipInputStream zin=new ZipInputStream(Files.newInputStream(dir.resolve(name+".zip")))) {if(zin.getNextEntry()==null)throw new IOException("no entry");streamBytes=consume(zin);}catch(Exception e){streamError=e.getClass().getSimpleName()+": "+e.getMessage();}
      System.out.print("{\"name\":"+quote(name)+",\"inflaterError\":"+quote(error)+",\"finished\":"+finished+",\"plainBytes\":"+total+",\"remaining\":"+remaining+",\"zipFileError\":"+quote(zipError)+",\"zipFileBytes\":"+zipBytes+",\"zipInputStreamError\":"+quote(streamError)+",\"zipInputStreamBytes\":"+streamBytes+"}");
    }
    System.out.println("\n]}");
  }
}
