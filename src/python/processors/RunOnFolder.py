#!/usr/bin/env python3
import os

# Specify the path to the broker directory
broker_directory = 'broker'

# Specify the path to the output directory
output_directory = 'blp'

# Get a list of files in the broker directory
file_list = os.listdir(broker_directory)

# Iterate over each file and run the command
for filename in file_list:
    input_path = os.path.join(broker_directory, filename)
    output_path = os.path.join(output_directory, f"{os.path.basename(filename)}.csv")

    # Construct and run the command
    command = f"python3 BrokerLogParser.py -i {input_path} -o {output_path}"
    os.system(command)
