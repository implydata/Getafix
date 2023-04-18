### Prerequisite 
 
This tools try to answer few question in the imply druid.  We try to achieve this by parsing imply broker logs. 
The output generated by this tool need to be ingested 

Install apache maven . Follow [this](https://maven.apache.org/install.html) to install Maven.

### Building the code.
Execute the command   `mvn package` inside `professional-services/brokerlog-parser` 

Prebuild releases are available in `s3://imply-support-ps/ps-tools/clusterReview/brokerlog-parser/`

### Running tool
 After building the package , a jar is created inside target folder. 
execute the below command to execute the bin
`java -cp brokerlog-parser-<version>-jar-with-dependencies.jar  -Ddruid.extensions.directory= <druid extension dir >  -Ddruid.extensions.loadList=[<List of extension > ]io.imply.cli.LogParseCli <input dir > <output dir> <account> <cluster id/name>`

eg :  java -cp brokerlog-parser-2.4-jar-with-dependencies.jar -Ddruid.extensions.directory="/Users/tijothomas/run/imply-2023.03.1/dist/druid/extensions/" -Ddruid.extensions.loadList="[\"druid-kinesis-indexing-service\",\"imply-sql-async\",\"imply-utility-belt\",\"druid-basic-security\",\"imply-nested-data\",\"druid-google-extensions\",\"druid-datasketches\",\"mysql-metadata-storage\",\"imply-druid-security\",\"druid-s3-extensions\",\"druid-kafka-indexing-service\",\"druid-multi-stage-query\",\"druid-histogram\",\"clarity-emitter\",\"indexed-table-loader\",\"druid-avro-extensions\",\"druid-lookups-cached-global\",\"simple-client-sslcontext\"]" io.imply.cli.LogParseCli /Users/tijothomas/Desktop/TG/  /Users/tijothomas/Desktop/output MyDruid Cluster1
OR
 
`java -cp brokerlog-parser-<version>>-SNAPSHOT-jar-with-dependencies.jar -Ddruid.extensions.directory= <dir> -Ddruid.extensions.loadList=[<List of extension >  io.imply.cli.LogParseCli <inputfile > <output file>`<account> <cluster id/name>

eg :  java -cp brokerlog-parser-2.4-jar-with-dependencies.jar -Ddruid.extensions.directory="/Users/tijothomas/run/imply-2023.03.1/dist/druid/extensions/" -Ddruid.extensions.loadList="[\"druid-kinesis-indexing-service\",\"imply-sql-async\",\"imply-utility-belt\",\"druid-basic-security\",\"imply-nested-data\",\"druid-google-extensions\",\"druid-datasketches\",\"mysql-metadata-storage\",\"imply-druid-security\",\"druid-s3-extensions\",\"druid-kafka-indexing-service\",\"druid-multi-stage-query\",\"druid-histogram\",\"clarity-emitter\",\"indexed-table-loader\",\"druid-avro-extensions\",\"druid-lookups-cached-global\",\"simple-client-sslcontext\"]" io.imply.cli.LogParseCli /Users/tijothomas/Desktop/TG/broker1.log  /Users/tijothomas/Desktop/output/parsedlog1.csv MyDruid Cluster1

#### ingesting to Druid 
Use the below spec to ingest in to druid.  change the `baseDir` to the input folder in the ingestion spec . 
```
{
  "type": "index_parallel",
  "spec": {
    "ioConfig": {
      "type": "index_parallel",
      "inputSource": {
        "type": "local",
        "baseDir": "<dir>",
        "filter": "*"
      },
      "inputFormat": {
        "type": "csv",
        "findColumnsFromHeader": false,
        "columns": [
          "queryid",
          "sqlqueryid",
          "implyDataCube",
          "implyFeature",
          "implyUser",
          "implyView",
          "priority",
          "recency",
          "duration",
          "filterseq",
          "filter"
        ]
      }
    },
    "tuningConfig": {
      "type": "index_parallel",
      "partitionsSpec": {
        "type": "dynamic"
      }
    },
    "dataSchema": {
      "dataSource": "TGoutput",
      "timestampSpec": {
        "column": "queryid",
        "format": "auto"
      },
      "dimensionsSpec": {
        "dimensions": [
          "sqlqueryid",
          "implyDataCube",
          "implyFeature",
          "implyUser",
          {
            "type": "long",
            "name": "implyView"
          },
          "priority",
          "recency",
          {
            "type": "long",
            "name": "duration"
          },
          {
            "type": "long",
            "name": "filterseq"
          },
          {
            "type": "long",
            "name": "filter"
          }
        ]
      },
      "granularitySpec": {
        "queryGranularity": "none",
        "rollup": false,
        "segmentGranularity": "day"
      }
    }
  }
}
```