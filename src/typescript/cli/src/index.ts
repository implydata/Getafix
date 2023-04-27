#!/usr/bin/env node
const { Command } = require("commander");
const fs = require("fs");
const path = require("path");
const figlet = require("figlet");

const program = new Command();

console.log(figlet.textSync("Getafix"));

program
  .version("1.0.0")
  .description("A CLI for executing Druid cluster review reports")
  .option("-i, --inputDir  [value]", "Input directory e.g., /var/tmp/localhost_20230425")
  .parse(process.argv);

const options = program.opts();

async function listDirContents(filepath: string) {
  try {
    const files = await fs.promises.readdir(filepath);
    const detailedFilesPromises = files.map(async (file: string) => {
      let fileDetails = await fs.promises.lstat(path.resolve(filepath, file));
      return { filename: file };
    });
    const detailedFiles = await Promise.all(detailedFilesPromises);
    console.table(detailedFiles);
  } catch (error) {
    console.error("Error occurred while reading the directory!", error);
  }
}

if (options.inputDir) {
  const filepath = typeof options.inputDir === "string" ? options.inputDir : __dirname;
  listDirContents(filepath);
}

if (!process.argv.slice(2).length) {
    program.outputHelp();
  }