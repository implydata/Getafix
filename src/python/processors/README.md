## BrokerLogParser.py

Working much the same as the Java brokerlog-parser, but written in Python

Provides a .csv with 1 row per query

```
./BrokerLogParser.py -h
usage: BrokerLogParser.py [-h] -i INPUTFILE -o OUTPUTFILE [-p REGEX_PATTERN]

Broker log query parser

options:
  -h, --help            show this help message and exit
  -i INPUTFILE, --inputFile INPUTFILE
                        Source Broker log file
  -o OUTPUTFILE, --outputFile OUTPUTFILE
                        Output csv file
```
To run on a dir `broker` full of log files and output to dir `blp`:
```
for i in `ls -d broker/*`
do
./BrokerLogParser.py -i $i -o blp/$(basename $i).csv
done
```

OR Use ```RunOnFolder.py```
