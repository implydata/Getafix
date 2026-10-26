## BrokerLogParser.py

Working much the same as the Java brokerlog-parser, but written in Python

Provides a .csv with 1 row per native query, plus a separate .csv of SQL queries.
Handles both the older (`query, stats`) and newer (`stats, query`) request log layouts, nested filters,
subqueries/joins/unions, and plain or `.gz` files. segmentMetadata queries are skipped unless `--includeSegmentMetadata` is given.

```
./BrokerLogParser.py -i INPUT [INPUT ...] -o OUTPUT [-p REGEX_PATTERN] [--sqlOutput FILE] [--noSql] [--includeSegmentMetadata] [-w WORKERS] [-q] [-d]
```
* Single file: `./BrokerLogParser.py -i broker.log -o broker.csv` (SQL queries go to `broker_sql.csv`)
* Directory: `./BrokerLogParser.py -i broker -o blp` writes `blp/<file>.csv` per log file and `blp/sql/<file>.csv`, in parallel

`-p` overrides line parsing with a regex that has named groups `query` and `result` (optionally `query_timestamp` and `ip`);
by default the tab-separated request log fields are detected automatically. `parseLog()` can be imported to parse a single file.

The `grouping` column lists the groupBy/topN dimensions (including subqueries).

A summary (query counts, top datasources, SQL errors, slowest SQL queries) is printed at the end; `-q` suppresses it.

Columns added after the original set (appended so existing ingestion specs keep working):
`sqlQueryId, identity, remoteAddr, statusCode, exception, dataSourceType, filterTypes, metrics, columns, granularity, intervals,
numIntervals, unboundedTime, lane, timeout, implyDataCube, implyFeature, implyView, sourceFile`.
`duration` is the queried time range with any end past the query time clamped to the query time; `recency`/`duration`
are blank when the interval start is unbounded (no time filter, flagged in `unboundedTime`).

`RunOnFolder.py` is no longer needed but still works.
