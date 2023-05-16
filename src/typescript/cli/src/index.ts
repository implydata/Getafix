#!/usr/bin/env node
const { Command } = require("commander");
const fs = require("fs");
const path = require("path");
const figlet = require("figlet");
const program = new Command();

export {};

console.log(figlet.textSync("Getafix"));

program
  .version("1.0.0")
  .description("A CLI for executing Druid cluster review reports")
  .option("-i, --inputDir  [value]", "Input directory e.g., ~/localhost_20230425")
  .parse(process.argv);
const options = program.opts();

async function getJsonFiles(filepath: string): Promise<Record<string, any>> {
  const files = await fs.promises.readdir(filepath);
  const jsonFiles = files.filter((file: string) => file.endsWith('.json'));
  const data: Record<string, any> = {};
  for (const file of jsonFiles) {
    const content = await fs.promises.readFile(path.join(filepath, file));
    const json = JSON.parse(content);
    data[file] = json;
  }
  return data;
}


async function main() {
  let filepath = '.';
  if (!process.argv.slice(2).length) {
    program.outputHelp();
  }
  if (options.inputDir) {
    filepath = typeof options.inputDir === "string" ? options.inputDir : __dirname;
  }
  const data = await getJsonFiles(filepath);
  console.log(data);
}

main();