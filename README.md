# Getafix

A cluster review scorecard used to evaluate the configuration and operation of Apache Druid clusters.

Designed to be executed in a cumulative way, depending on your interest and ability to collect information.

## Analysis types planned

1. Run API queries against the cluster to get information about datasources, compaction etc. *
2. Add node size info and and compare to Druid cluster guidelines for this
3. Collect Broker logs to understand best practices for partitioning, tiering
4. Collect metrics (Clarity / Logs / Prometheus) information to identify hotspots / trends

## Data collection methods

### Druid API collector

**Currently collected**

| API query | Description |
| --- | --- |
| compaction | Configuration of compaction for each applicable datasource |
| compaction status | Current status of compaction for each applicable datasource |
| coordinator dynamic config | Current configuration of the coordinator dynamic configuration |
| datasources | Detailed information for all segments contained in each datasource |
| lookups | Configuration information for all configured lookups |
| overlord dynamic config | Current configuration of the overlord dynamic configuration |
| retention | Current retention policies for all configured datasources |
| segments | Number of segments, average size and average number of rows for each datasource |
| servers | List of servers (services) which comprise the cluster |
| supervisors | Details of configured supervisors |
| tasks | A snapshot of recently run tasks |
| workers | Number of workers available |

******To add******

`/status/properties` from all available services to understand Druid tuning parameters

### Log upload

### Metrics collection

## Rule based evaluation

Evaluate data based on [cDMN](https://cdmn.readthedocs.io/en/latest/notation.html) - can be expressed in XLS or DMN file types

file:///Users/khoondert/Documents/Data/Dev/temp/Getafix.html