package io.imply.cli;


import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.InjectableValues;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.inject.Injector;
import com.google.inject.Module;
import io.imply.LogEntry;
import io.imply.parser.LogParser;
import io.imply.util.NoopLookupExtractorFactoryContainerProvider;
import io.imply.util.ToolExprMacroTable;
import org.apache.druid.common.config.NullHandling;
import org.apache.druid.guice.*;
import org.apache.druid.initialization.DruidModule;
import org.apache.druid.jackson.DefaultObjectMapper;
import org.apache.druid.js.JavaScriptConfig;
import org.apache.druid.math.expr.ExprMacroTable;
import org.apache.druid.query.Query;
import org.apache.druid.query.dimension.DimensionSpec;
import org.apache.druid.query.groupby.GroupByQuery;
import org.apache.druid.query.lookup.LookupExtractorFactoryContainerProvider;
import org.apache.druid.query.topn.TopNQuery;
import org.apache.druid.segment.VirtualColumn;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.joda.time.Interval;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.Hashtable;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import static org.apache.druid.query.Query.*;

/**
 *
 *
 */
public class LogParseCli
{
  public static final String OUTPUT_DATE_FORMAT = "yyyy-MM-dd HH:mm:ss";
  public static final String DEFAULT_OUTPUT_POSTFIX = "output.csv";
  SimpleDateFormat dateFormat = new SimpleDateFormat(OUTPUT_DATE_FORMAT);
  private final Logger logger = Logger.getLogger(this.getClass().getName());
  private ObjectMapper mapper = null;
  static {
    NullHandling.initializeForTests();
  }
    public static void main( String[] args ) throws Exception
    {

      LogParseCli  cli = new LogParseCli();

      cli.init("");

      String implyCloudAccountId = "Unknown";
      if (args.length > 2){
        implyCloudAccountId = args[2];
      }
      String clusterId = "default";
      if (args.length > 3){
        clusterId = args[3];
      }
      if(args[0] != null && args[1] != null )
        cli.processInput(args[0],args[1],implyCloudAccountId,clusterId);
    }

    public void init(String extnConfig ) throws JsonProcessingException
    {
      final Injector injector = GuiceInjectors.makeStartupInjector();

      ParserCli cli = new ParserCli();
      mapper = new DefaultObjectMapper();
      final ExtensionsConfig config = injector.getInstance(ExtensionsConfig.class);
      final ExtensionsLoader extnLoader = new ExtensionsLoader(config);

      for (Module  module :extnLoader.getModules()) {
        DruidModule druidModule =(DruidModule) module;
        if(!(druidModule.getJacksonModules().isEmpty())) {
          for (com.fasterxml.jackson.databind.Module jacksonModule : druidModule.getJacksonModules()) {
            mapper.registerModule(jacksonModule);
            logger.info(" -> " + jacksonModule);
          }
        }
      }
      List<Module> modules = (List<Module>) cli.getModules();
      for (Module module: modules) {
        if (module instanceof DruidModule) {
          DruidModule druidModule = (DruidModule) module;
          for (com.fasterxml.jackson.databind.Module jacksonModule : druidModule.getJacksonModules()) {
            mapper.registerModule(jacksonModule);
            logger.info(jacksonModule.getModuleName() + "-"+jacksonModule.toString());
          }
        }
      }
      // Extra mapping
      mapper.registerModules(NestedDataModule.getJacksonModulesList());
      //NoopLookupExtractorFactoryContainerProvider mappings are actually created by the leader services. We are mocking it here.
      NoopLookupExtractorFactoryContainerProvider provider = new NoopLookupExtractorFactoryContainerProvider();
      mapper.setInjectableValues(
          new InjectableValues.Std()
              .addValue(LookupExtractorFactoryContainerProvider.class, provider)
              .addValue(ExprMacroTable.class.getName(), ToolExprMacroTable.INSTANCE)
                  .addValue(JavaScriptConfig.class.getName(), JavaScriptConfig.getEnabledInstance())

      );
    }

  public  void processInput(String input , String output,String implyCloudAccountId , String clusterId) throws Exception
  {
    LogParser logParser = new LogParser(mapper);
    logParser.setParseForQueryType(GROUP_BY);
    logParser.setParseForQueryType(SCAN);
    logParser.setParseForQueryType(TIMESERIES);
    logParser.setParseForQueryType(TOPN);

    File inputFile = new File(input);
    File outputFile = new File(output);
    if (inputFile.isDirectory()) {
      createOrReplaceDir(outputFile);
    } else {
      createOrReplaceFile(outputFile);
    }

    if (inputFile.isDirectory()) {
      Files.list(Paths.get(inputFile.getAbsolutePath()))
           .forEach(inputPath -> {
             try {
               logger.info("Processing  log "+ inputPath.getFileName());
               processFile(inputPath.toFile(), outputFile, logParser,implyCloudAccountId,clusterId);
             }
             catch (Exception e) {
               e.printStackTrace();
               logger.log(Level.ERROR , " Error while processing File " + inputPath.toString() +" Error Message " + e.getMessage());
             }
           });
    } else {
      processFile(inputFile,outputFile, logParser, implyCloudAccountId,clusterId);
    }
  }

  private void processFile(File inputFile ,File outputFile, LogParser logParser,String implyCloudAccountId,String clusterId) throws Exception
  {
    logParser.setLogFile(inputFile);
    if(outputFile.isDirectory()){
      outputFile = new File (outputFile.getAbsolutePath() + File.separatorChar+ inputFile.getName() + "_"+DEFAULT_OUTPUT_POSTFIX);
    }
    FileWriter parseDataWriter = new FileWriter( outputFile);
    writeHeader(parseDataWriter);
    while(logParser.hasNext()){
        LogEntry entry = logParser.next();
        if (entry == null ){
         break;
        }
        writeFilters(parseDataWriter, entry,implyCloudAccountId, clusterId);
        writeGroupingDim(parseDataWriter, entry,implyCloudAccountId,clusterId);
 //     writeMetric(parseDataWriter, entry,implyCloudAccountId,clusterId);
        parseDataWriter.flush();
    }
    parseDataWriter.close();
  }

//  private void writeMetrics(FileWriter parseDataWriter, LogEntry entry, String implyCloudAccountId, String clusterId) {
//    if(entry.type.equalsIgnoreCase(TOPN) || entry.type.equalsIgnoreCase(GROUP_BY) ) {
//      Query query = entry.query;
//
//      VirtualColumn[] queryVirtualCols = query.getVirtualColumns().getVirtualColumns();
//      if(entry.type.equalsIgnoreCase(TOPN) ){
//        TopNQuery topN =  (TopNQuery)query;
//        topN.getAggregatorSpecs().
//      }
//      int length = query.getVirtualColumns().getVirtualColumns().length;
//    }
//  }

  private void writeGroupingDim(FileWriter parseDataWriter, LogEntry entry, String implyCloudAccountId, String clusterId) throws Exception
  {
    if(entry.type.equalsIgnoreCase(TOPN) || entry.type.equalsIgnoreCase(GROUP_BY) ) {
      Query query = entry.query;
      VirtualColumn[] queryVirtualCols = query.getVirtualColumns().getVirtualColumns();
      Hashtable<String , Set<String>> extractedVirtualCol = new Hashtable<String, Set<String>>();
      long recency = entry.eventTime.getTime() - ((Interval) entry.query.getIntervals().get(0)).getStart()
                                                                                                 .toLocalDateTime()
                                                                                                 .toDate()
                                                                                                 .getTime();
      long duration = ((Interval) entry.query.getIntervals().get(0)).getEndMillis()
                        - ((Interval) entry.query.getIntervals().get(0)).getStartMillis();
      for (VirtualColumn queryVirtualCol : queryVirtualCols) {
        if (queryVirtualCol.getOutputName() != null) {
          extractedVirtualCol.put(queryVirtualCol.getOutputName(), new LinkedHashSet<String>(queryVirtualCol.requiredColumns()));
        }
      }
      if (query.getType().equalsIgnoreCase( TOPN)){
        TopNQuery topN = (TopNQuery) query ;
        String dimension  = topN.getDimensionSpec().getDimension();
        // col existing in virtual
        if(extractedVirtualCol.get(dimension) == null ){
          writeCSVData(parseDataWriter, entry, 0, "", dimension , recency, duration,implyCloudAccountId,clusterId);
        }else{
          writeCSVData(parseDataWriter, entry, 0,"",extractedVirtualCol.get(dimension).stream().reduce ("", (x,y)->x+"|"+y  ) , recency, duration,implyCloudAccountId,clusterId);
        }
      }else if (query.getType().equalsIgnoreCase(GROUP_BY)){
        StringBuilder sb = new StringBuilder();
        GroupByQuery groupBy = (GroupByQuery) query ;
        List<DimensionSpec> groupbys = groupBy.getDimensions();
        //int count = 0;
        Set<String> groupByCols = new TreeSet<String>();
        for (DimensionSpec groupby : groupbys) {
          if (extractedVirtualCol.get(groupby) == null) {
            groupByCols.add(groupby.getDimension());
            //sb.append(groupby.getDimension()).append('|');
            //           writeCSVData(parseDataWriter, entry, count , groupby.getDimension(), recency, duration);
          } else {
            groupByCols.addAll(extractedVirtualCol.get(groupby.getDimension()));
            //sb.append(extractedVirtualCol.get(groupby.getDimension()).stream().reduce("", (x, y) -> x + "|" + y));
          }
        }
        writeCSVData(
                parseDataWriter,
                entry,
                0,
                "",
                groupByCols.stream().reduce("", (x, y) -> x + "|" + y) ,
                recency,
                duration,
                implyCloudAccountId,
                clusterId
            );
      }else{
        throw new Exception("Only TopN or group by is allowed. This type is "+query.getType());
      }
    }

  }

  private void writeFilters(FileWriter parseDataWriter, LogEntry entry,String implyCloudAccountId,String clusterId) throws IOException {
    if(entry.query.getFilter() != null ) {
      int count =0;
      for (String x : entry.query.getFilter().getRequiredColumns()) {
        long recency = entry.eventTime.getTime() - ((Interval) entry.query.getIntervals().get(0)).getStart().toLocalDateTime().toDate().getTime();
        long duration = ((Interval) entry.query.getIntervals().get(0)).getEndMillis() - ((Interval) entry.query.getIntervals().get(0)).getStartMillis() ;
        writeCSVData(parseDataWriter, entry, count, x,"", recency, duration,implyCloudAccountId,clusterId);
      }
    }else{
      long recency = entry.eventTime.getTime() - ((Interval) entry.query.getIntervals().get(0)).getStartMillis() ;
      long duration = ((Interval) entry.query.getIntervals().get(0)).getEndMillis() - ((Interval) entry.query.getIntervals().get(0)).getStartMillis() ;
      writeCSVData(parseDataWriter, entry, 0, null,"", recency, duration,implyCloudAccountId,clusterId);
    }
  }

  private void writeHeader(FileWriter parseDataWriter) throws IOException
  {
    parseDataWriter.write( "eventtime,querytype,datasource," +
                           "queryid,sqlqueryid,"+
                           "implyDataCube,implyFeature," +
                           "implyUser,implyView,"+
                           "priority,recency,duration,"+
                           "filterseq,filter,grouping,"+
                           "clusterId");
    parseDataWriter.write("\n");
    parseDataWriter.flush();
  }

  private void writeCSVData(
      FileWriter parseDataWriter,
      LogEntry entry,
      int count,
      String filter,
      String grouping,
      long recency,
      long duration,
      String implyCloudAccountId,
      String clusterId

  ) throws IOException
  {
    /*
    TODO : This doesnot support sub query and join .
     Sub queries are really important  Need to add this feature
     */
    // eventtime, querytype, datasource
    if(entry.query.getDataSource().getTableNames().toArray().length >0){
      parseDataWriter.write(dateFormat.format(entry.eventTime) + "," + entry.type + "," + entry.query.getDataSource().getTableNames().toArray()[0] + "," +
                  // queryid,sqlqueryid
                  entry.query.getId() + "," + entry.query.getSqlQueryId() + "," +
                  // implyDataCube, implyFeature
                  entry.query.getContext().get("implyDataCube") + "," + entry.query.getContext().get("implyFeature") + "," +
                  // implyUser, implyView
                  entry.query.getContext().get("implyUser") + "," + entry.query.getContext().get("implyView") + "," +
                  // priority, recency, duration
                  entry.query.getContext().get("priority") + ","+ recency/1000 + ","+duration/1000  + ","+
                  //filterseq , filter
                  count + "," + filter +","+grouping+ ","+
                  //implyCloudAccountId , clusterId
                            implyCloudAccountId +","+clusterId);
      parseDataWriter.write("\n");
      parseDataWriter.flush();
    }else{
      logger.warn("Queryid :"+entry.query.getId() +" not supported");
    }
  }

  private  void createOrReplaceFile(File outputFile) throws IOException
  {
    outputFile.createNewFile();
    logger.log(Level.INFO , " Created outputFile "+ outputFile);
  }

  private  void createOrReplaceDir(File outputFile) {
    if(outputFile.exists()){
      outputFile.delete();
    }
    outputFile.mkdirs();
    logger.log(Level.INFO , " Created output folder "+ outputFile);
  }
}
