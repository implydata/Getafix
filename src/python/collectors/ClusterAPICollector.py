#!/usr/bin/env python3

import requests
import argparse
import sys
import tempfile
import zipfile
import json
import os
import datetime

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def checkOptions():
    parser = argparse.ArgumentParser(description = 'Getafix - Cluster API Info Collector')
    parser.add_argument('Router', action='store', type=str, help='Router URL with protocol and port')
    parser.add_argument('ClusterName', action='store', type=str, help='Cluster Name')
    parser.add_argument('-z', '--zipfile', action='store_true', dest='zipfile', help='Generate zipfile')
    parser.add_argument('-k', '--kerberos', action='store_true', dest='kerberos', help='''
                        Enable kerberos authentication (must already have valid ticket''')
    parser.add_argument('-u', '--user', action='store', type=str, dest='user', help='Username')
    parser.add_argument('-p', '--password', action='store', type=str, dest='password', help='Password')
    parser.add_argument('-t', '--token', action='store', type=str, dest='token', help='Token (like YRtWa... - no "Basic"')
    options = parser.parse_args()

    if options.kerberos:
        from requests_kerberos import HTTPKerberosAuth, REQUIRED
        global kerberos_auth
        kerberos_auth = HTTPKerberosAuth(mutual_authentication=REQUIRED, sanitize_mutual_error_response=False)
    
    if options.token:
        options.auth = True
    else:
        options.auth = False

    if options.user:
        if not options.password:
            print('Please enter username and password, or token')
            sys.exit(2)
        else:
            import base64
            options.auth = True
            userPass = bytes(options.user + ':' + options.password, encoding='utf-8')
            options.token = base64.b64encode(userPass).decode("utf-8")
    
    return options


def getRequest(URL, options):
    fullURL = options.Router + URL
    if options.kerberos:
        req = requests.get(fullURL, auth=kerberos_auth, verify=False)

    elif options.auth:
        headers = {'Authorization': 'Basic ' + options.token}
        req = requests.get(fullURL, headers=headers, verify=False)

    else:
        req = requests.get(fullURL, verify=False)
    try:
        JSON = req.json()
    except json.decoder.JSONDecodeError:
        JSON = {}
    return JSON
    

def postRequest(URL, query, options):
    fullURL = options.Router + URL
    if options.kerberos:
        headers = {'Content-Type': 'application/json'}
        req = requests.post(fullURL, headers=headers, json=qery, auth=kerberos_auth, verify=False)

    elif options.auth:
        headers = {'Content-Type': 'application/json', 'Authorization': 'Basic ' + options.token}
        req = requests.post(fullURL, headers=headers, json=query, verify=False)
    else:
        headers = {'Content-Type': 'application/json'}
        req = requests.post(fullURL, headers=headers, json=query, verify=False)

    JSON = req.json()
    return JSON


def getSegments(options):
    queryJSON = {'query': """
        SELECT "datasource", count("segment_id") as segmentCount, AVG("size") as avgSize, avg("num_rows") as avgRows 
        FROM sys.segments  
        GROUP BY "datasource"
        """
    }
    URL = '/druid/v2/sql'
    return postRequest(URL, queryJSON, options)


def getServers(options):
    queryJSON = {'query': """
        SELECT "server" AS "service", "server_type", "tier", "host", "plaintext_port", "tls_port", "curr_size", "max_size"
        FROM sys.servers 
        ORDER BY "service" DESC
        """
    }
    URL = '/druid/v2/sql'
    return postRequest(URL, queryJSON, options)


def getCompaction(options):
    URL = '/druid/coordinator/v1/config/compaction'
    return getRequest(URL, options)


def getCompactionStatus(options):
    URL = '/druid/coordinator/v1/compaction/status'
    return getRequest(URL, options)


def getSupervisors(options):
    URL = '/druid/indexer/v1/supervisor?full'
    return getRequest(URL, options)


def getTasks(options):
    queryJSON = {'query': """
        WITH tasks AS (
          SELECT "task_id", "group_id", "type", "datasource", "created_time", "location", "duration", "error_msg",
          CASE
            WHEN "error_msg" = 'Shutdown request from user' THEN 'CANCELED' 
            WHEN "status" = 'RUNNING' THEN "runner_status" 
            ELSE "status" 
          END AS "status"
          FROM sys.tasks
        )
        SELECT "task_id", "group_id", "type", "datasource", "created_time", "location", "duration", "error_msg", "status"
        FROM tasks
        ORDER BY "created_time" DESC
        """
        }
    URL = '/druid/v2/sql'
    return postRequest(URL, queryJSON, options)


def getRetention(options):
    URL = '/druid/coordinator/v1/rules?full'
    return getRequest(URL, options)


def getDatasources(options):
    URL = '/druid/coordinator/v1/metadata/datasources?full'
    return getRequest(URL, options)


def getCoordinatorSettings(options):
    URL = '/druid/coordinator/v1/config'
    return getRequest(URL, options)


def getOverlordSettings(options):
    URL = '/druid/indexer/v1/worker'
    return getRequest(URL, options)


def getLookups(options):
    URL = '/druid/coordinator/v1/lookups/config/all'
    return getRequest(URL, options)


def getWorkers(options):
    URL = '/druid/indexer/v1/workers'
    return getRequest(URL, options)


def collectAPIData(options):
    outputDir = options.ClusterName + '_' + datetime.date.today().isoformat()
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    with open(outputDir + "/compaction.json", "w") as outfile:  
        json.dump(getCompaction(options), outfile, indent=2)
    with open(outputDir + "/compactionStatus.json", "w") as outfile:  
        json.dump(getCompactionStatus(options), outfile, indent=2)
    with open(outputDir + "/supervisors.json", "w") as outfile:
        json.dump(getSupervisors(options), outfile, indent=2)
    with open(outputDir + "/tasks.json", "w") as outfile:
        json.dump(getTasks(options), outfile, indent=2)
    with open(outputDir + "/retention.json", "w") as outfile:
        json.dump(getRetention(options), outfile, indent=2)
    with open(outputDir + "/datasources.json", "w") as outfile:
        json.dump(getDatasources(options), outfile, indent=2)
    with open(outputDir + "/coordinatorDynamic.json", "w") as outfile:
        json.dump(getCoordinatorSettings(options), outfile, indent=2)
    with open(outputDir + "/overlordDynamic.json", "w") as outfile:
        json.dump(getOverlordSettings(options), outfile, indent=2)
    with open(outputDir + "/servers.json", "w") as outfile:
        json.dump(getServers(options), outfile, indent=2)
    with open(outputDir + "/segments.json", "w") as outfile:
        json.dump(getSegments(options), outfile, indent=2)
    with open(outputDir + "/lookups.json", "w") as outfile:
        json.dump(getLookups(options), outfile, indent=2)
    with open(outputDir + "/workers.json", "w") as outfile:
        json.dump(getWorkers(options), outfile, indent=2)

def collectAPIDataZip(options):
    fileDetails = options.ClusterName + '_' + datetime.date.today().isoformat()
    with zipfile.ZipFile(fileDetails + '.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(os.path.join(fileDetails, 'compaction.json'), json.dumps(getCompaction(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'compactionStatus.json'), json.dumps(getCompactionStatus(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'supervisors.json'), json.dumps(getSupervisors(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'tasks.json'), json.dumps(getTasks(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'retention.json'), json.dumps(getRetention(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'datasources.json'), json.dumps(getDatasources(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'coordinatorDynamic.json'), json.dumps(getCoordinatorSettings(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'overlordDynamic.json'), json.dumps(getOverlordSettings(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'servers.json'), json.dumps(getServers(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'segments.json'), json.dumps(getSegments(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'lookups.json'), json.dumps(getLookups(options), indent=2))
        archive.writestr(os.path.join(fileDetails, 'workers.json'), json.dumps(getWorkers(options), indent=2))     
    print("Zipfile", fileDetails + ".zip created successfully")   
        
def main():
    options = checkOptions()
    if options.zipfile:
        collectAPIDataZip(options)
    else:
        collectAPIData(options)


if __name__ == '__main__':
    main()
