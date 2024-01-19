#!/usr/bin/env python3
import sys
import csv
import json
import argparse
import datetime

csv.field_size_limit(sys.maxsize)

def checkOptions():
    parser = argparse.ArgumentParser(description = 'Broker log query parser')
    parser.add_argument('-i', '--inputFile', required=True, action='store', type=str, dest='inputFile', help='Source Broker log file')
    parser.add_argument('-o', '--outputFile', required=True, action='store', dest='outputFile', help='Output csv file')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Extra debugging')
    options = parser.parse_args()

    return options


def main():
    global options
    options = checkOptions()

    with open(options.inputFile, "r") as inFile:
        with open(options.outputFile, "w") as outFile:
            writer = csv.writer(outFile)
            writer.writerow(["eventtime", "querytype", "datasource", "queryid", "priority", "recency", "duration", "queryTime", "queryBytes", "success", "filters", "aggregations", "implyUser", "query"])
            tsv_file = csv.reader(inFile, delimiter = "\t")
            for inLine in tsv_file:
                try:
                    query = json.loads(inLine[2])
                    queryResult = json.loads(inLine[3])
                except:
                    continue
                try:
                     logTime = inLine[0].split()[5]
                     logDate = datetime.datetime.strptime(logTime, "%Y-%m-%dT%H:%M:%S.%fZ")
                except:
                     continue
                if query['queryType'] == 'segmentMetadata':
                    continue
                elif query['queryType'] == 'union':
                    dataSource = "'" + query['query']['dataSource']['name'] + "'"
                    queryId = query['query']['context']['queryId']
                    try:
                        priority = query['query']['context']['priority']
                    except:
                        priority = 'Null'
                    intervals = query['query']['intervals']['intervals']
                else:
                    if query['dataSource']['type'] == 'table':
                        try:
                            dataSource = query['dataSource']['name']
                        except:
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
                    except:
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
                                    intervalStart = datetime.datetime.strptime(interval.split('/')[0], "%Y-%m-%dT%H:%M:%S.%fZ")
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
                        filterList.append(query['filter']['dimension'].replace('"',''))
                    elif query['filter']['type'] == 'columnComparison':
                        filterList.append(query['filter']['dimensions'].replace('"',''))
                    elif query['filter']['type'] == 'and' or query['filter']['type'] == 'or':
                        for filters in query['filter']['fields']:
                            try:
                                if filters['type'] == 'selector':
                                    filterList.append(filters['dimension'].replace('"',''))
                                elif filters['type'] == 'not':
                                    filterList.append(filters['field']['dimension'].replace('"',''))
                            except:
                                if options.debug:
                                    print('Filter Exception:', filters)
                                filterList.append(json.dumps(filters))
                                continue
                except:
                    continue
                filterList = list(dict.fromkeys(filterList))
                if options.debug:
                    print(str(filterList))
                aggregationsList = []
                try:
                    for aggregations in query['aggregations']:
                        aggregationsList.append(aggregations['type'].replace('"',''))
                except:
                    continue
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
                #outLine = [ logTime, query['queryType'], dataSource, queryId, priority, int(round(recency.total_seconds())), int(round(duration.total_seconds())), queryTime, queryBytes, success, str(filterList), json.dumps(query)]
                writer.writerow([logTime, query['queryType'], dataSource, queryId, priority, int(round(recency.total_seconds())), int(round(duration.total_seconds())), queryTime, queryBytes, success, (', '.join(filterList)), (', '.join(aggregationsList)), implyUser, json.dumps(query)])

if __name__ == '__main__':
    main()   
