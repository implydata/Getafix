package io.imply.parser;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.AnnotationIntrospector;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.introspect.AnnotatedMember;
import io.imply.LogEntry;
import org.apache.druid.guice.GuiceAnnotationIntrospector;
import org.apache.druid.query.BaseQuery;
import org.apache.druid.query.groupby.GroupByQuery;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainer;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainerProvider;
import org.apache.druid.query.scan.ScanQuery;
import org.apache.druid.query.timeseries.TimeseriesQuery;
import org.apache.druid.query.topn.TopNQuery;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.joda.time.DateTime;

import javax.xml.bind.DatatypeConverter;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.apache.druid.query.Query.GROUP_BY;
import static org.apache.druid.query.Query.SCAN;
import static org.apache.druid.query.Query.TIMESERIES;
import static org.apache.druid.query.Query.TOPN;
public class LogParser
    //implements Iterator<LogEntry>
{
  private static final String NAME = "name";
  private static final String FIELD_NAME = "fieldName";
  private static final int LG_K = 2;
  private static final String TGT_HLL_TYPE = "HLL_6";
  private static final boolean ROUND = true;
  private String regex  = "(.*)\\s.*\\s(.*)\\s(.*)$";
  private Pattern pattern =null;

  private Set<String> queryTypes = new LinkedHashSet<String>();
  private List<String> logLines;
  private File logFile ;
  private Iterator logIterator;
  //private SimpleDateFormat = new SimpleDateFormat("YYYY-MM-dd");
  private Logger logger ;
  private  ObjectMapper mapper ;
   private Matcher matcher ;
  public LogParser(ObjectMapper mapper) throws IOException
  {
    logger = Logger.getLogger(this.getClass().getName());
    this.mapper = mapper;

  }
  public void setRegexPattern(String regex)
  {
    if(regex != null && regex.length() !=0){
      this.regex = regex;
    }
    this.pattern = Pattern.compile(this.regex);
  }
  public void setParseForQueryType(String types)
  {
    queryTypes.add(types);
  }

  public void setLogFile(File file) throws IOException
  {
    this.logFile =file;
    logLines = Files.readAllLines(Paths.get(file.getAbsolutePath()), StandardCharsets.UTF_8);
    logIterator = logLines.listIterator();
  }

  public boolean hasNext()
  {
    return logIterator.hasNext();

  }

  public LogEntry next()
  {
    for (Iterator it = logIterator; it.hasNext(); ) {
      String logLine = (String) it.next();

      if (logLine.contains("{\"queryType")) {
        Matcher matcher = pattern.matcher(logLine);
        if(!matcher.find()) {
          System.out.println( "Unable to match the pattern  " + pattern.pattern());
        }
//        int queryTimeIndex = logLine.indexOf("{\"query/time" );
//        String queryTime =logLine.substring(queryTimeIndex +14 ,  logLine.indexOf(",",queryTimeIndex) );
        for (String type : queryTypes) {
          if (logLine.contains("queryType\":\""+type)) {
//            String date = logLine.substring(0, logLine.indexOf("\t"));
            String date = matcher.group(1);
            Calendar cal = DatatypeConverter.parseDateTime(date.trim());
            DateTime dateTime = new DateTime(cal);
            String line =null;
//            if (logLine.indexOf("{\"queryType") > 0)
            if (matcher.group(2).length() >0)
              line = matcher.group(2).trim();
//              if (queryTimeIndex <=0){
//               logger.log(Level.WARN ,  "Unable to parse log line in "+logFile.getAbsolutePath() + " starting with  line " + logLine.substring(0, 60));
//              } else {
//                line = logLine.substring(logLine.indexOf("{\"queryType"), queryTimeIndex);
//              }
            if (line == null || line.length() ==0)
              break;
            try {
              BaseQuery query = null;
              query = createQueryObject(line, type);
              long queryTimeVal = 0;
              try{
                String metric = matcher.group(3);
                int queryTimeIndex = metric.indexOf("{\"query/time" ) ;
                String queryTime =metric.substring(queryTimeIndex +14 ,  metric.indexOf(",",queryTimeIndex) );
                queryTimeVal = Long.parseLong(queryTime);
              }catch (Exception e){
                System.out.println(" unable to parse execution time in  Line:" + line );
                queryTimeVal = 0;
              }
              return new LogEntry(dateTime.toDate(), type, query, queryTimeVal);
            }
            catch (Exception e) {
              System.out.println(" Line:" + line );
              e.printStackTrace();
            }
          }
        }
      }
    }
    return null;
  }

  private BaseQuery createQueryObject(String line, String type ) throws JsonProcessingException
  {

    BaseQuery query =  null;

    switch (type) {
      case GROUP_BY:
        query  =  mapper.readValue(line ,GroupByQuery.class );
        return query;

      case SCAN:
        query  =  mapper.readValue(line ,ScanQuery.class );
        return query;

      case TIMESERIES:
        query  =  mapper.readValue(line ,TimeseriesQuery.class );
        return query;

      case TOPN:
        query  =  mapper.readValue(line ,TopNQuery.class );
        return query;
    }
    return null;
  }

  private static class NoopLookupExtractorFactoryContainerProvider implements LookupExtractorFactoryContainerProvider
  {
    private NoopLookupExtractorFactoryContainerProvider() {
    }

    public Set<String> getAllLookupNames() {
      return Collections.emptySet();
    }

    public Optional<LookupExtractorFactoryContainer> get(String lookupName) {
      return Optional.empty();
    }
  }

  public static AnnotationIntrospector makeAnnotationIntrospector()
  {
    // Prepare annotationIntrospector with similar logic, except skip Guice loading
    // because most tests don't use Guice injection.
    return new GuiceAnnotationIntrospector()
    {
      @Override
      public Object findInjectableValueId(AnnotatedMember m)
      {
        return null;
      }
    };
  }

}
