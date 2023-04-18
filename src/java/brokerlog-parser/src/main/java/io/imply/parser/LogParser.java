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

  private Set<String> queryTypes = new LinkedHashSet<String>();
  private List<String> logLines;
  private File logFile ;
  private Iterator logIterator;
  //private SimpleDateFormat = new SimpleDateFormat("YYYY-MM-dd");
  private Logger logger ;
  private  ObjectMapper mapper ;
  public LogParser(ObjectMapper mapper) throws IOException
  {
    logger = Logger.getLogger(this.getClass().getName());
    this.mapper = mapper;
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
      if (logLine.contains("LoggingRequestLogger")) {

        for (String type : queryTypes) {
          if (logLine.contains("queryType\":\""+type)) {
            String date = logLine.substring(logLine.indexOf("LoggingRequestLogger -")+22 , logLine.indexOf("\t"));

            Calendar cal = DatatypeConverter.parseDateTime(date.trim());
            DateTime dateTime = new DateTime(cal);
            String line =null;
            if (logLine.indexOf("{\"queryType") > 0)
              if (logLine.indexOf("{\"query/time") <=0){
               logger.log(Level.WARN ,  "Unable to parse log line in "+logFile.getAbsolutePath() + " starting with  line " + logLine.substring(0, 60));
              } else {
                line = logLine.substring(logLine.indexOf("{\"queryType"), logLine.indexOf("{\"query/time"));
              }
            if (line == null)
              break;
            try {
              BaseQuery query = null;
              query = createQueryObject(line, type);

              return new LogEntry(dateTime.toDate(), type, query);
            }
            catch (JsonProcessingException e) {
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
