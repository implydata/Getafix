#!/usr/bin/env python3
import os
import argparse

def process_file(input_path, output_path):
    # Construct and run the command
    command = f"python3 BrokerLogParser.py -i {input_path} -o {output_path}"
    os.system(command)

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Process broker files and generate CSV output.')

    # Add input and output path arguments
    parser.add_argument('-i', '--input', type=str, required=True, help='Path to the broker directory')
    parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output directory')

    # Parse command line arguments
    args = parser.parse_args()

    # Get a list of files in the broker directory
    file_list = os.listdir(args.input)

    # Create the output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    # Iterate over each file and run the command
    for filename in file_list:
        input_path = os.path.join(args.input, filename)
        output_path = os.path.join(args.output, f"{os.path.basename(filename)}.csv")

        # Process the file
        process_file(input_path, output_path)

if __name__ == "__main__":
    main()
