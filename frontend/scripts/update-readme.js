import fs from "fs";
import path from "path";

const coverageFile = path.resolve("coverage/coverage-summary.json");
const readmeFile = path.resolve("README.md");

if (!fs.existsSync(coverageFile)) {
  console.error(
    "Coverage summary file not found! Run tests with coverage first.",
  );
  process.exit(1);
}

const coverageData = JSON.parse(fs.readFileSync(coverageFile, "utf8"));
const total = coverageData.total;

// Get percentages
const stmts = total.statements.pct;
const lines = total.lines.pct;
const funcs = total.functions.pct;
const branches = total.branches.pct;

// Use the lower of lines/statements for the main badge
const mainPct = Math.min(stmts, lines);

// Determine color
let color = "red";
if (mainPct >= 90) color = "brightgreen";
else if (mainPct >= 80) color = "green";
else if (mainPct >= 70) color = "yellowgreen";
else if (mainPct >= 60) color = "yellow";
else if (mainPct >= 50) color = "orange";

let readmeContent = fs.readFileSync(readmeFile, "utf8");

// 1. Update Badge
const badgeRegex =
  /!\[Coverage Percentage\]\(https:\/\/img\.shields\.io\/badge\/coverage-.*-.*\)/;
const newBadge = `![Coverage Percentage](https://img.shields.io/badge/coverage-${mainPct}%25-${color})`;
readmeContent = readmeContent.replace(badgeRegex, newBadge);

// 2. Update Table via markers
const tableStart = "<!-- START_COVERAGE_TABLE -->";
const tableEnd = "<!-- END_COVERAGE_TABLE -->";

const newTable = `| Category       | Coverage   |
| :------------- | :--------- |
| **Statements** | **${stmts}%** |
| **Lines**      | **${lines}%** |
| **Functions**  | **${funcs}%** |
| **Branches**   | **${branches}%** |`;

if (readmeContent.includes(tableStart) && readmeContent.includes(tableEnd)) {
  const startIndex = readmeContent.indexOf(tableStart) + tableStart.length;
  const endIndex = readmeContent.indexOf(tableEnd);
  readmeContent =
    readmeContent.substring(0, startIndex) +
    "\n\n" +
    newTable +
    "\n\n" +
    readmeContent.substring(endIndex);
} else {
  // Fallback to the old line-by-line replacement if markers are missing
  const lines_array = readmeContent.split("\n");
  let modified = false;

  for (let i = 0; i < lines_array.length; i++) {
    if (lines_array[i].includes("**Statements**")) {
      lines_array[i] = `| **Statements** | **${stmts}%** |`;
      modified = true;
    }
    if (lines_array[i].includes("**Lines**")) {
      lines_array[i] = `| **Lines** | **${lines}%** |`;
      modified = true;
    }
    if (lines_array[i].includes("**Functions**")) {
      lines_array[i] = `| **Functions** | **${funcs}%** |`;
      modified = true;
    }
    if (lines_array[i].includes("**Branches**")) {
      lines_array[i] = `| **Branches** | **${branches}%** |`;
      modified = true;
    }
  }

  if (modified) {
    readmeContent = lines_array.join("\n");
  }
}

fs.writeFileSync(readmeFile, readmeContent);
console.log(`Updated README.md with coverage: ${mainPct}%`);
