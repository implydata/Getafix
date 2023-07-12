# Cluster API Collector

Cluster  API collector  is a Python program which collects information of the API query such as compaction, compaction status and datasources etc.
### Information collected
| API query | Description | Collected from |
| --- | --- | --- |
| compaction | Configuration of compaction for each applicable datasource | ```/druid/coordinator/v1/config/compaction```
| compaction status | Current status of compaction for each applicable datasource | ```/druid/coordinator/v1/compaction/status```
| coordinator dynamic config | Current configuration of the coordinator dynamic configuration |```/druid/coordinator/v1/config```
| datasources | Detailed information for all segments contained in each datasource | ``/druid/coordinator/v1/metadata/datasources?full``
| lookups | Configuration information for all configured lookups |```/druid/coordinator/v1/lookups/config/all```
| overlord dynamic config | Current configuration of the overlord dynamic configuration |```/druid/indexer/v1/worker```
| retention | Current retention policies for all configured datasources |```/druid/coordinator/v1/rules?full```
| segments | Number of segments, average size and average number of rows for each datasource |sys.segments  
| servers | List of servers (services) which comprise the cluster | sys.servers  
| supervisors | Details of configured supervisors |``/druid/indexer/v1/supervisor?full``
| tasks | A snapshot of recently run tasks | sys.tasks 
| workers | Number of workers available |``/druid/indexer/v1/workers``

### Running the Python file
Run the python file along with the arguments : Router and ClusterName<br>
Note: Provide URL with protocol (http/https) and port number .<br>
Example :```python3 ClusterAPICollector.py http://localhost:8888 my-cluster```

### Expected Output
The expected output is a directory of json files with all the above information.<br> 
The directory is created in the same folder from where the python scprit is executed with file name in the format of < ClusterName >_< date > <br>
The output can be compressed by using ```-z``` as argument.

Example :```python3 ClusterAPICollector.py http://localhost:8888 my-cluster -z```

