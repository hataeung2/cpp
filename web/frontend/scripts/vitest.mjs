// `npm test` runs Vitest through this file (spec 070-25, KI-052).
//
// On Windows, a working directory whose drive letter is lower case (a VS Code terminal, cmd after a
// lower-case `cd /d`) makes Node load Vitest twice: once under the lower-case path the CLI was started
// from and once under the upper-case path the test files resolve to. Every test file then fails with
// "Vitest failed to find the current suite". This file moves to the same folder with an upper-case
// drive letter first and starts the Vitest CLI from there; elsewhere it only starts the CLI.
import { fileURLToPath, pathToFileURL } from 'node:url';

const upperDrive = (path) => path.replace(/^[a-z](?=:)/, (d) => d.toUpperCase());

process.chdir(upperDrive(process.cwd()));
const cli = upperDrive(fileURLToPath(new URL('../node_modules/vitest/vitest.mjs', import.meta.url)));
await import(pathToFileURL(cli).href);
