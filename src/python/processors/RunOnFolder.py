#!/usr/bin/env python3
import os
import argparse
import re

def process_file(input_path, output_path, pattern=None, debug=False):
    # If a pattern is provided, apply it to the file content
    # if pattern:
    #     try:
    #         with open(input_path, 'r') as infile:
    #             lines = infile.readlines()
    #         filtered_lines = [line for line in lines if re.search(pattern, line)]

    #         temp_input_path = f"{input_path}.filtered"
    #         with open(temp_input_path, 'w') as temp_file:
    #             temp_file.writelines(filtered_lines)

    #         input_path = temp_input_path
    #     except Exception as e:
    #         print(f"Error applying pattern to {input_path}: {e}")
    #         return

    # Construct and run the command
    command = f"python3 BrokerLogParser.py -i {input_path} -o {output_path}"
    if pattern:
        command += f" -p \"{pattern}\""
    if debug:
        command += f" -d "
        print(f"Running command: {command}")
    os.system(command)

    # Clean up the temporary filtered file if it was created
    if pattern and os.path.exists(input_path) and input_path.endswith(".filtered"):
        os.remove(input_path)

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Process broker files and generate CSV output.')

    # Add input and output path arguments
    parser.add_argument('-i', '--input', type=str, required=True, help='Path to the broker directory')
    parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output directory')

    # Add additional arguments
    parser.add_argument('-p', '--pattern', required=False, action='store', type=str, dest='pattern', help='Regex pattern for log parsing')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Enable extra debugging')

    # Parse command line arguments
    args = parser.parse_args()

    # Traverse the input directory recursively
    for root, _, files in os.walk(args.input):
        for filename in files:
            input_path = os.path.join(root, filename)

            # Recreate the directory structure in the output directory
            relative_path = os.path.relpath(input_path, args.input)
            output_path = os.path.join(args.output, f"{relative_path}.csv")

            # Create the necessary directories for the output path
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if args.debug:
                print(f"Processing file: {input_path} -> {output_path}")

            # Process the file
            process_file(input_path, output_path, pattern=args.pattern, debug=args.debug)

if __name__ == "__main__":
    main()
