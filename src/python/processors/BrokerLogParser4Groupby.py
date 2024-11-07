#!/usr/bin/env python3
import sys
import csv
import json
import argparse
import datetime
import re

csv.field_size_limit(sys.maxsize)

def checkOptions():
    parser = argparse.ArgumentParser(description='Broker log query parser')
    parser.add_argument('-i', '--inputFile', required=True, action='store', type=str, dest='inputFile', help='Source Broker log file')
    parser.add_argument('-o', '--outputFile', required=True, action='store', dest='outputFile', help='Output csv file')
    parser.add_argument('-p', '--pattern', required=False, action='store', type=str, dest='pattern', help='Regex pattern for log parsing')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Extra debugging')
    options = parser.parse_args()

    return options

def main():
    global options
    options = checkOptions()

    default_pattern = r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d{3})\s+(?P<log_level>\w+)\s+\[(?P<thread>.*?)\]\s+(?P<logger>[^\s]+)\s+-\s+(?P<query_timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?P<query>\{.*\})\s+(?P<result>\{.*\})$'
    log_pattern = re.compile(options.pattern if options.pattern else default_pattern)

    with open(options.inputFile, "r") as inFile:
        with open(options.outputFile, "w") as outFile:
            writer = csv.writer(outFile)
            writer.writerow(["eventtime", "querytype", "datasource", "queryid", "priority", "recency", "duration", "queryTime", "queryBytes", "success", "filters", "dimensions", "aggregations", "implyUser", "query"])
            for line in inFile:
                match = log_pattern.match(line)
                if not match:
                    continue
                try:
                    query = json.loads(match.group('query'))
                    queryResult = json.loads(match.group('result'))
                except json.JSONDecodeError:
                    continue
                try:
                    logTime = match.group('query_timestamp')
                    logDate = datetime.datetime.strptime(logTime, "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    continue
                try:
                    query['queryType']
                except KeyError:
                    continue    
                if query['queryType'] == 'segmentMetadata':
                    continue
                elif query['queryType'] == 'union':
                    dataSource = "'" + query['query']['dataSource']['name'] + "'"
                    queryId = query['query']['context']['queryId']
                    try:
                        priority = query['query']['context']['priority']
                    except KeyError:
                        priority = 'Null'
                    intervals = query['query']['intervals']['intervals']
                else:
                    if query['dataSource']['type'] == 'table':
                        try:
                            dataSource = query['dataSource']['name']
                        except KeyError:
                            dataSource = ''
                            for ds in query['dataSource']['dataSources']:
                                if len(dataSource) > 1:
                                    dataSource = dataSource + ",'" + ds['name'] + "'"
                                else:
                                    dataSource = dataSource + "'" + ds['name'] + "'"
                    else:
                        dataSource = 'inline'
                    queryId = query['context']['queryId']
                    try:
                        priority = query['context']['priority']
                    except KeyError:
                        priority = 'Null'
                    intervalStart = 0
                    intervalEnd = 0
                    try:
                        intervals = query['intervals']['intervals']
                        if intervals and len(intervals) > 0:
                            interval = intervals[0]
                            interval_parts = interval.split('/')
                            if len(interval_parts) >= 1:
                                try:
                                    intervalStart = datetime.datetime.strptime(interval_parts[0], "%Y-%m-%dT%H:%M:%S.%fZ")
                                except ValueError:
                                    pass
                            if len(interval_parts) >= 2:
                                try:
                                    intervalEnd = datetime.datetime.strptime(interval.split('/')[1], "%Y-%m-%dT%H:%M:%S.%fZ")
                                except (ValueError, IndexError):
                                    pass
                    except (KeyError, IndexError):
                        pass
                filterList = []
                try:
                    if query['filter']['type'] == 'selector' or query['filter']['type'] == 'regex':
                        filterList.append(query['filter']['dimension'].replace('"', ''))
                    elif query['filter']['type'] == 'columnComparison':
                        filterList.append(query['filter']['dimensions'].replace('"', ''))
                    elif query['filter']['type'] == 'and' or query['filter']['type'] == 'or':
                        for filters in query['filter']['fields']:
                            try:
                                if filters['type'] == 'selector':
                                    filterList.append(filters['dimension'].replace('"', ''))
                                elif filters['type'] == 'not':
                                    filterList.append(filters['field']['dimension'].replace('"', ''))
                            except KeyError:
                                if options.debug:
                                    print('Filter Exception:', filters)
                                filterList.append(json.dumps(filters))
                                continue
                    filterList = list(dict.fromkeys(filterList))
                except KeyError:
                    pass
                if options.debug:
                    print(str(filterList))

                # Extracting dimensions
                dimensionsList = []
                try:
                    if 'dimension' in query:
                        if isinstance(query['dimension'], dict):
                            dimensionsList.append(query['dimension']['dimension'])
                        elif isinstance(query['dimension'], list):
                            for dimension in query['dimension']:
                                dimensionsList.append(dimension['dimension'])
                except KeyError:
                    pass

                aggregationsList = []
                try:
                    for aggregations in query['aggregations']:
                        aggregationsList.append(aggregations['type'].replace('"', ''))
                except KeyError:
                    pass
                try:
                    intervalStart = datetime.datetime.strptime(interval.split('/')[0], "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    intervalStart = datetime.datetime.strptime('0001-01-01T00:00:00.000Z', "%Y-%m-%dT%H:%M:%S.%fZ")
                try:
                    intervalEnd = datetime.datetime.strptime(interval.split('/')[1], "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    intervalEnd = datetime.datetime.strptime('9999-12-31T23:59:59.999Z', "%Y-%m-%dT%H:%M:%S.%fZ")
                duration = intervalEnd - intervalStart
                recency = logDate - intervalStart
                queryTime = queryResult['query/time']
                queryBytes = queryResult['query/bytes']
                success = queryResult['success']
                jsonquery = json.dumps(query)
                data = json.loads(jsonquery)
                try:
                    implyUser = data["context"]["implyUser"]
                except KeyError:
                    implyUser = ''
                writer.writerow([logTime, query['queryType'], dataSource, queryId, priority, int(round(recency.total_seconds())), int(round(duration.total_seconds())), queryTime, queryBytes, success, ', '.join(filterList), ', '.join(dimensionsList), ', '.join(aggregationsList), implyUser, json.dumps(query)])

if __name__ == '__main__':
    main()

