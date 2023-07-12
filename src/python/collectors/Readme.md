# Cluster API Collector

Cluster  API collector  is a Python program which collects information of the API query such as compaction, compaction status and datasources etc.
### Information collected
| API query | Description | Collected from |
| --- | --- | --- |
| compaction | Configuration of compaction for each applicable datasource | '/druid/coordinator/v1/config/compaction' |
| compaction status | Current status of compaction for each applicable datasource | '/druid/coordinator/v1/compaction/status'
| coordinator dynamic config | Current configuration of the coordinator dynamic configuration |'/druid/coordinator/v1/config'
| datasources | Detailed information for all segments contained in each datasource | '/druid/coordinator/v1/metadata/datasources?full'
| lookups | Configuration information for all configured lookups |'/druid/coordinator/v1/lookups/config/all'
| overlord dynamic config | Current configuration of the overlord dynamic configuration |'/druid/indexer/v1/worker'
| retention | Current retention policies for all configured datasources |'/druid/coordinator/v1/rules?full'
| segments | Number of segments, average size and average number of rows for each datasource |sys.segments  
| servers | List of servers (services) which comprise the cluster | sys.servers  
| supervisors | Details of configured supervisors |'/druid/indexer/v1/supervisor?full'
| tasks | A snapshot of recently run tasks | sys.tasks 
| workers | Number of workers available |'/druid/indexer/v1/workers'

### Running the Python file
Run the python file along with the arguments : router and ClusterName

note: while giving router give it with Router URI with protocol and port.
Example :python3 ClusterAPICollector.py http://localhost:8888 my-cluster

### Expected Output
The expected output is a directory of json files of all the seprate API  Queries 
which is located in the same folder as the ClusterAPICollector python file.
If zipfile is required then add -z at the end of the already given argument.

Example :python3 ClusterAPICollector.py http://localhost:8888 my-cluster -z

