#!/usr/bin/env python3
"""
Broker request log parser.

Reads Druid broker logs (log4j lines written by LoggingRequestLogger, or raw request log files)
and writes one CSV row per native query, plus a separate CSV of SQL queries.

Handles both request log layouts:
    timestamp \t remoteAddr \t nativeQuery \t queryStats          (older Druid)
    timestamp \t remoteAddr \t queryStats  \t nativeQuery         (newer Druid)
    timestamp \t remoteAddr \t "" \t queryStats \t sqlQuery        (SQL)

A custom regex can be given with -p; it needs named groups 'query' and 'result' (stats), and optionally
'query_timestamp' and 'ip'.
"""
import os
import sys
import csv
import json
import gzip
import re
import argparse
import datetime
import collections
from multiprocessing import Pool

csv.field_size_limit(sys.maxsize)

NATIVE_HEADER = ["eventtime", "querytype", "datasource", "queryid", "priority", "recency", "duration", "queryTime", "queryBytes",
                 "success", "filters", "grouping", "aggregations", "implyUser", "query",
                 # columns added after the original layout, kept at the end so existing ingestion specs still work
                 "sqlQueryId", "identity", "remoteAddr", "statusCode", "exception", "dataSourceType", "filterTypes", "metrics",
                 "columns", "granularity", "intervals", "numIntervals", "unboundedTime", "lane", "timeout", "implyDataCube", "implyFeature",
                 "implyView", "sourceFile"]

SQL_HEADER = ["eventtime", "sqlQueryId", "identity", "remoteAddr", "sqlQueryTime", "planningTimeMs", "sqlQueryBytes", "success",
              "statusCode", "exception", "nativeQueryIds", "implyUser", "query", "context", "sourceFile"]

# Filter types whose referenced column lives under 'dimension' or 'column'
FILTER_COMPOUND = ('and', 'or')


def checkOptions():
    parser = argparse.ArgumentParser(description = 'Broker log query parser')
    parser.add_argument('-i', '--input', '--inputFile', required=True, nargs='+', dest='inputs', help='Source broker log file(s) or directory')
    parser.add_argument('-o', '--output', '--outputFile', required=True, dest='output',
                        help='Output csv file, or a directory (one csv per input file, SQL queries under <dir>/sql/)')
    parser.add_argument('-p', '--pattern', required=False, action='store', type=str, dest='pattern',
                        help='Regex pattern for log parsing (named groups: query, result, query_timestamp, ip)')
    parser.add_argument('--sqlOutput', dest='sqlOutput', help='SQL query csv when --output is a single file (default: <output>_sql.csv)')
    parser.add_argument('--noSql', action='store_true', dest='noSql', help='Do not write SQL query output')
    parser.add_argument('--includeSegmentMetadata', action='store_true', dest='includeSegmentMetadata',
                        help='Include internal segmentMetadata queries (skipped by default)')
    parser.add_argument('-w', '--workers', type=int, default=os.cpu_count() or 1, dest='workers', help='Parallel workers for multiple files')
    parser.add_argument('-q', '--quiet', action='store_true', dest='quiet', help='Do not print the summary')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Extra debugging')
    return parser.parse_args()


def parseTimestamp(value):
    """ISO8601 -> naive UTC datetime, or None if unparseable / outside datetime range (e.g. Druid's 'eternity' bounds)."""
    try:
        ts = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None
    if ts.tzinfo is not None:
        ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return ts


def joinList(values):
    return ', '.join(str(v) for v in dict.fromkeys(values) if v is not None and v != '')


def getDataSources(ds, names, types):
    """Recursively collect table names and datasource types."""
    if isinstance(ds, str):
        names.append(ds)
        types.append('table')
        return
    if not isinstance(ds, dict):
        return
    dsType = ds.get('type', '')
    types.append(dsType)
    if dsType == 'table':
        names.append(ds.get('name'))
    elif dsType == 'union':
        for sub in ds.get('dataSources', []):
            getDataSources(sub, names, types)
    elif dsType == 'query':
        getDataSources(ds.get('query', {}).get('dataSource'), names, types)
    elif dsType == 'join':
        getDataSources(ds.get('left'), names, types)
        getDataSources(ds.get('right'), names, types)
    elif dsType in ('restrict', 'filter', 'unnest'):
        getDataSources(ds.get('base'), names, types)
    elif dsType == 'lookup':
        names.append('lookup:' + str(ds.get('lookup')))
    elif dsType == 'inline':
        names.append('inline')


def getFilters(f, columns, types, debug=False):
    """Recursively collect columns referenced by a filter and the filter types used."""
    if not isinstance(f, dict):
        return
    fType = f.get('type', '')
    types.append(fType)
    if fType in FILTER_COMPOUND:
        for sub in f.get('fields', []):
            getFilters(sub, columns, types, debug)
    elif fType in ('not', 'istrue', 'isfalse'):
        getFilters(f.get('field'), columns, types, debug)
    elif fType == 'columnComparison':
        for dim in f.get('dimensions', []):
            columns.append(dim.get('dimension') if isinstance(dim, dict) else dim)
    elif fType == 'expression':
        columns.append('expr:' + str(f.get('expression')))
    elif fType in ('true', 'false'):
        pass
    elif 'dimension' in f:
        columns.append(f['dimension'])
    elif 'column' in f:
        columns.append(f['column'])
    elif debug:
        print('Unhandled filter:', json.dumps(f), file=sys.stderr)


def getAggregations(aggs, types, metrics, filterColumns, filterTypes, debug=False):
    for agg in aggs or []:
        aggType = agg.get('type', '')
        if aggType == 'filtered':
            inner = agg.get('aggregator', {})
            types.append('filtered(' + inner.get('type', '') + ')')
            metrics.append(inner.get('fieldName'))
            getFilters(agg.get('filter'), filterColumns, filterTypes, debug)
        else:
            types.append(aggType)
            metrics.append(agg.get('fieldName'))
            for field in agg.get('fieldNames', []) or []:
                metrics.append(field)


def getDimensions(query):
    dims = []
    for dim in query.get('dimensions', []) or []:
        dims.append(dim.get('dimension') if isinstance(dim, dict) else dim)
    topNDim = query.get('dimension')
    if topNDim is not None:
        dims.append(topNDim.get('dimension') if isinstance(topNDim, dict) else topNDim)
    return dims


def getIntervals(query):
    intervals = query.get('intervals', [])
    if isinstance(intervals, dict):
        if 'intervals' in intervals:
            intervals = intervals['intervals']
        else:
            intervals = [seg.get('itvl') for seg in intervals.get('segments', [])]
    return [i for i in intervals if isinstance(i, str)]


def getGranularity(query):
    gran = query.get('granularity')
    if isinstance(gran, dict):
        return gran.get('period') or gran.get('duration') or gran.get('type')
    return gran


def intervalStats(intervals, eventTime):
    """
    Returns (recency, duration) in seconds.
    recency  = event time - earliest interval start (blank if unbounded)
    duration = sum of interval lengths, with the end clamped to the event time so 'start/eternity' gives the real lookback
    """
    starts = []
    duration = 0
    bounded = True
    for interval in intervals:
        startStr, _, endStr = interval.partition('/')
        start = parseTimestamp(startStr)
        end = parseTimestamp(endStr)
        if start is None:
            bounded = False
            continue
        starts.append(start)
        if end is None or (eventTime is not None and end > eventTime):
            end = eventTime if eventTime is not None and eventTime > start else end
        if end is None:
            bounded = False
            continue
        duration += (end - start).total_seconds()
    recency = int(round((eventTime - min(starts)).total_seconds())) if starts and eventTime is not None else ''
    return recency, (int(round(duration)) if bounded and intervals else '')


def splitLine(line, pattern=None):
    """Returns (eventtime, remoteAddr, stats, payload) or None if the line is not a request log line."""
    if pattern is not None:
        match = pattern.match(line.rstrip('\r\n'))
        if not match:
            return None
        groups = match.groupdict()
        try:
            first = json.loads(groups['result'])
            second = json.loads(groups['query'])
        except (ValueError, KeyError, TypeError):
            return None
        # stats/query are identified by content, so the group names can't get swapped
        if 'queryType' in first or ('query' in first and 'success' not in first):
            first, second = second, first
        return groups.get('query_timestamp') or '', groups.get('ip') or '', first, second
    parts = line.rstrip('\r\n').split('\t')
    if len(parts) < 4 or not parts[-1].startswith('{') or not parts[-2].startswith('{'):
        return None
    try:
        first = json.loads(parts[-2])
        second = json.loads(parts[-1])
    except ValueError:
        return None
    if 'success' in first or 'query/time' in first or 'sqlQuery/time' in first:
        stats, payload = first, second
    else:
        stats, payload = second, first
    # The request log timestamp is the last token of the first field (after any log4j prefix)
    eventTime = parts[0].rsplit(' ', 1)[-1]
    return eventTime, parts[1], stats, payload


def subQueries(ds):
    """Queries nested inside a datasource (query datasources, join sides, unions)."""
    if not isinstance(ds, dict):
        return []
    dsType = ds.get('type')
    if dsType == 'query':
        return [ds.get('query', {})]
    if dsType == 'join':
        return subQueries(ds.get('left')) + subQueries(ds.get('right'))
    if dsType == 'union':
        return [q for sub in ds.get('dataSources', []) for q in subQueries(sub)]
    if dsType in ('restrict', 'filter', 'unnest'):
        return subQueries(ds.get('base'))
    return []


def outputNames(query):
    names = set()
    for key in ('dimensions', 'aggregations', 'postAggregations', 'virtualColumns'):
        for item in query.get(key, []) or []:
            if isinstance(item, dict):
                names.add(item.get('outputName') or item.get('name'))
    # SQL time-floor groupings are emitted as a timestamp result field (e.g. d0) by the inner query
    names.add((query.get('context', {}) or {}).get('timestampResultField'))
    return names


def isEternity(intervals):
    return all(parseTimestamp(i.partition('/')[0]) is None and parseTimestamp(i.partition('/')[2]) is None for i in intervals)


def nativeRow(eventTime, remoteAddr, stats, query, sourceFile, debug):
    eventDate = parseTimestamp(eventTime)
    context = query.get('context', {}) or {}
    queryType = query.get('queryType', '')
    if queryType == 'union':
        # legacy union query wraps the real query
        query = query.get('query', query)
        context = query.get('context', context) or context

    dsNames, dsTypes = [], []
    getDataSources(query.get('dataSource'), dsNames, dsTypes)

    # Walk the outer query and any subqueries; columns that are just outputs of an inner query (d0, a0, ...) are dropped
    filterColumns, filterTypes, aggTypes, metrics, dimensions, columns = [], [], [], [], [], []
    intervals = []
    granularity = None
    pending = [query]
    while pending:
        level = pending.pop(0)
        inner = subQueries(level.get('dataSource'))
        innerNames = set().union(*(outputNames(q) for q in inner)) if inner else set()
        levelFilters, levelMetrics = [], []
        getFilters(level.get('filter'), levelFilters, filterTypes, debug)
        getAggregations(level.get('aggregations'), aggTypes, levelMetrics, levelFilters, filterTypes, debug)
        filterColumns += [c for c in levelFilters if c not in innerNames]
        metrics += [c for c in levelMetrics if c not in innerNames]
        dimensions += [c for c in getDimensions(level) if c not in innerNames]
        if (level.get('context', {}) or {}).get('timestampResultField'):
            dimensions.append('__time')
        levelGranularity = getGranularity(level)
        if granularity is None or (str(granularity).lower() == 'all' and levelGranularity):
            granularity = levelGranularity
        columns += [c for c in level.get('columns', []) or [] if c not in innerNames]
        levelIntervals = getIntervals(level)
        if not intervals or (isEternity(intervals) and levelIntervals):
            intervals = levelIntervals
        pending += inner

    recency, duration = intervalStats(intervals, eventDate)
    unbounded = [side for side, idx in (('start', 0), ('end', 2)) if intervals and any(parseTimestamp(i.partition('/')[idx]) is None for i in intervals)]

    return [eventTime, queryType, joinList(dsNames), context.get('queryId', query.get('id', '')), context.get('priority', 'Null'),
            recency, duration, stats.get('query/time', ''), stats.get('query/bytes', ''), stats.get('success', ''),
            joinList(filterColumns), joinList(dimensions), joinList(aggTypes), context.get('implyUser', ''), json.dumps(query),
            context.get('sqlQueryId', ''), stats.get('identity', ''), remoteAddr, stats.get('statusCode', ''), stats.get('exception', ''),
            joinList(dsTypes), joinList(filterTypes), joinList(metrics), joinList(columns), granularity,
            ' '.join(intervals), len(intervals), '/'.join(unbounded), context.get('lane', ''), context.get('timeout', ''),
            context.get('implyDataCube', ''), context.get('implyFeature', ''), context.get('implyView', ''), sourceFile]


def sqlRow(eventTime, remoteAddr, stats, payload, sourceFile):
    context = payload.get('context', {}) or {}
    return [eventTime, context.get('sqlQueryId', ''), stats.get('identity', ''), remoteAddr, stats.get('sqlQuery/time', ''),
            stats.get('sqlQuery/planningTimeMs', ''), stats.get('sqlQuery/bytes', ''), stats.get('success', ''),
            stats.get('statusCode', ''), stats.get('exception', ''), context.get('nativeQueryIds', ''), context.get('implyUser', ''),
            payload.get('query', ''), json.dumps(context), sourceFile]


def openInput(path):
    if path.endswith('.gz'):
        return gzip.open(path, 'rt', errors='replace')
    return open(path, 'r', errors='replace')


def parseFile(job):
    """Parse one input file. Returns summary counters."""
    inputFile, outputFile, sqlFile, opts = job
    summary = collections.Counter()
    slowest = []
    sourceFile = os.path.basename(inputFile)
    pattern = re.compile(opts['pattern']) if opts.get('pattern') else None
    sqlOut = open(sqlFile, 'w', newline='') if sqlFile else None
    sqlWriter = csv.writer(sqlOut) if sqlOut else None
    if sqlWriter and opts['writeHeader']:
        sqlWriter.writerow(SQL_HEADER)
    with openInput(inputFile) as inFile, open(outputFile, 'w', newline='') as outFile:
        writer = csv.writer(outFile)
        if opts['writeHeader']:
            writer.writerow(NATIVE_HEADER)
        for line in inFile:
            summary['lines'] += 1
            parsed = splitLine(line, pattern)
            if parsed is None:
                continue
            eventTime, remoteAddr, stats, payload = parsed
            try:
                if 'queryType' in payload:
                    if payload['queryType'] == 'segmentMetadata' and not opts['includeSegmentMetadata']:
                        summary['skipped segmentMetadata'] += 1
                        continue
                    row = nativeRow(eventTime, remoteAddr, stats, payload, sourceFile, opts['debug'])
                    writer.writerow(row)
                    summary['native'] += 1
                    summary['native:' + row[1]] += 1
                    summary['ds:' + row[2]] += 1
                    if row[9] is False:
                        summary['native failed'] += 1
                    if 'start' in row[27]:
                        summary['native no time filter'] += 1
                elif 'query' in payload:
                    if sqlWriter:
                        row = sqlRow(eventTime, remoteAddr, stats, payload, sourceFile)
                        sqlWriter.writerow(row)
                        if isinstance(row[4], int):
                            slowest.append((row[4], row[1], row[12][:200]))
                    summary['sql'] += 1
                    if stats.get('success') is False:
                        summary['sql failed'] += 1
                        summary['sqlerr:' + str(stats.get('exception', ''))[:150]] += 1
                else:
                    summary['unrecognised'] += 1
            except Exception as e:
                summary['errors'] += 1
                if opts['debug']:
                    print('Error parsing line in', sourceFile, ':', repr(e), line[:500], file=sys.stderr)
    if sqlOut:
        sqlOut.close()
    slowest = sorted(slowest, reverse=True)[:10]
    return summary, slowest


def collectInputs(inputs):
    files = []
    for path in inputs:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isfile(full) and not name.startswith('.') and name not in ('config', 'lock', 'state'):
                    files.append(full)
        else:
            files.append(path)
    return files


def printSummary(summary, slowest):
    print()
    print('Lines read:          ', summary['lines'])
    print('Native queries:      ', summary['native'], '(failed: %d)' % summary['native failed'])
    print('  no time filter:    ', summary['native no time filter'])
    print('SQL queries:         ', summary['sql'], '(failed: %d)' % summary['sql failed'])
    print('segmentMetadata skip:', summary['skipped segmentMetadata'])
    print('Parse errors:        ', summary['errors'], '(use -d for details)' if summary['errors'] else '')
    for title, prefix in (('Native query types', 'native:'), ('Top datasources', 'ds:'), ('Top SQL errors', 'sqlerr:')):
        items = sorted(((v, k[len(prefix):]) for k, v in summary.items() if k.startswith(prefix)), reverse=True)[:10]
        if items:
            print('\n' + title + ':')
            for count, name in items:
                print('  %8d  %s' % (count, name or '(none)'))
    if slowest:
        print('\nSlowest SQL queries (ms):')
        for ms, sqlId, sql in slowest:
            print('  %8d  %s  %s' % (ms, sqlId, ' '.join(sql.split())[:120]))


def parseLog(input_path, output_path, pattern=None, debug=False, sql_path=None, includeSegmentMetadata=False):
    """Parse a single broker log file to csv. Returns the summary counter."""
    opts = {'includeSegmentMetadata': includeSegmentMetadata, 'debug': debug, 'writeHeader': True, 'pattern': pattern}
    summary, _ = parseFile((input_path, output_path, sql_path, opts))
    return summary


def main():
    global options
    options = checkOptions()

    inputFiles = collectInputs(options.inputs)
    if not inputFiles:
        sys.exit('No input files found')

    opts = {'includeSegmentMetadata': options.includeSegmentMetadata, 'debug': options.debug, 'writeHeader': True,
            'pattern': options.pattern}
    jobs = []
    if os.path.isdir(options.output) or len(inputFiles) > 1 or options.output.endswith(os.sep):
        # One csv per input file, as RunOnFolder.py used to produce
        os.makedirs(options.output, exist_ok=True)
        sqlDir = None if options.noSql else os.path.join(options.output, 'sql')
        if sqlDir:
            os.makedirs(sqlDir, exist_ok=True)
        for inputFile in inputFiles:
            name = os.path.basename(inputFile) + '.csv'
            jobs.append((inputFile, os.path.join(options.output, name), os.path.join(sqlDir, name) if sqlDir else None, opts))
    else:
        sqlFile = None if options.noSql else (options.sqlOutput or os.path.splitext(options.output)[0] + '_sql.csv')
        jobs.append((inputFiles[0], options.output, sqlFile, opts))

    summary = collections.Counter()
    slowest = []
    workers = max(1, min(options.workers, len(jobs)))
    if workers > 1:
        with Pool(workers) as pool:
            results = pool.imap_unordered(parseFile, jobs)
            for count, (fileSummary, fileSlowest) in enumerate(results, 1):
                summary.update(fileSummary)
                slowest.extend(fileSlowest)
                if not options.quiet:
                    print('Processed %d/%d files' % (count, len(jobs)), end='\r', file=sys.stderr)
    else:
        for job in jobs:
            fileSummary, fileSlowest = parseFile(job)
            summary.update(fileSummary)
            slowest.extend(fileSlowest)

    if not options.quiet:
        printSummary(summary, sorted(slowest, reverse=True)[:10])


if __name__ == '__main__':
    main()
