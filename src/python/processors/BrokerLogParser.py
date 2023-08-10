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
    options = parser.parse_args()

    return options

def main():
    global options
    options = checkOptions()

    with open(options.inputFile, "r") as inFile:
        with open(options.outputFile, "w") as outFile:
            writer = csv.writer(outFile)
            writer.writerow(["eventtime", "querytype", "datasource", "queryid", "priority", "recency", "duration", "queryTime", "queryBytes", "success", "filters", "implyUser", "query"])
            tsv_file = csv.reader(inFile, delimiter = "\t")
            for inLine in tsv_file:
                try:
                    query = json.loads(inLine[2])
                    queryResult = json.loads(inLine[3])
                except:
                    continue
                try:
                     logTime = inLine[0].split()[0]
                     logDate = datetime.datetime.strptime(logTime, "%Y-%m-%dT%H:%M:%S.%fZ")
                except:
                     continue
                if query['queryType'] == 'segmentMetadata':
                    continue
                elif query['queryType'] == 'union':
                    dataSource = "'" + query['dataSource']['name'] + "'"
                    queryId = query['context']['queryId']
                    try:
                        priority = query['context']['priority']
                    except:
                        priority = 'Null'
                    intervals = query['intervals']['intervals']
                elif query['queryType'] == 'groupBy':
                    if query['dataSource']['type'] == 'union':
                       dataSource = "'" + query['dataSource']['dataSources'][0]['name'] + "|" + query['dataSource']['dataSources'][1]['name'] + "'"
                    else:
                       dataSource = "'" + query['dataSource']['name'] + "'"
                    queryId = query['context']['queryId']
                    try:
                        priority = query['query']['context']['priority']
                    except:
                        priority = 'Null'
                    intervals = query['intervals']['intervals']
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
                    intervals = query['intervals']['intervals']
                interval = intervals[0]
                filterList = []
                try:
                    if query['filter']['type'] == 'selector' or query['filter']['type'] == 'regex':
                        filterList.append(query['filter']['dimension'].replace('"',''))
                    elif query['filter']['type'] == 'columnComparison':
                        filterList.append(query['filter']['dimensions'].replace('"',''))
                    elif query['filter']['type'] == 'and' or query['filter']['type'] == 'or':
                        for filters in query['filter']['fields']:
                            filterList.append(filters['dimension'].replace('"',''))
                except:
                    continue
                #print(str(filterList))
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
                writer.writerow([logTime, query['queryType'], dataSource, queryId, priority, int(round(recency.total_seconds())), int(round(duration.total_seconds())), queryTime, queryBytes, success, (', '.join(filterList)), implyUser, json.dumps(query)])

if __name__ == '__main__':
    main()   
