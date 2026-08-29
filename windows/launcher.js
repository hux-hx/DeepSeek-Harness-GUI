#!/usr/bin/env node
"use strict";
/**
 * DeepSeek Harness Desktop — Windows Launcher
 * 
 * This script:
 * 1. Finds the installed dsh binary
 * 2. Sets up the app home directory
 * 3. Launches dsh web as a supervised sidecar
 * 4. Waits for the UI to become available
 * 5. Opens it in the default browser (or tracks the process)
 */

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");
const http = require("http");

const APP_NAME = "DeepSeek Harness";
const APP_DIR_NAME = "DeepSeekHarnessDesktop";

// ── helpers ──────────────────────────────────────────────────────────────────

function log(msg) {
  const ts = new Date().toISOString().replace(/\..*/, "T");
  console.log(`[${ts}] ${msg}`);
}

function findDsh() {
  try {
    const where = execSync("where dsh", { encoding: "utf8", windowsHide: true })
      .trim()
      .split(/\r?\n/)[0];
    if (where && fs.existsSync(where)) return where;
  } catch {}
  return null;
}

function getDataDir() {
  const appData = process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
  return path.join(appData, APP_DIR_NAME);
}

function waitForHttp(url, timeoutMs = 90_000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    function check() {
      http.get(url, (res) => {
        if (res.statusCode === 200) resolve(url);
        else setTimeout(check, 500);
      }).on("error", () => {
        if (Date.now() < deadline) setTimeout(check, 500);
        else reject(new Error(`dsh web did not become ready within ${timeoutMs / 1000}s`));
      });
    }
    check();
  });
}

function extractUrlFromOutput(lines) {
  for (const line of lines) {
    const m = line.match(/dsh web:\s*(\S+)/);
    if (m) return m[1];
  }
  return null;
}

// ── main ─────────────────────────────────────────────────────────────────────

async function main() {
  log(`Starting ${APP_NAME}...`);

  const dsh = findDsh();
  if (!dsh) {
    console.error(`Error: "${APP_NAME}" requires DeepSeek Harness (dsh).`);
    console.error("");
    console.error("Install it first:");
    console.error("  npm install -g @deepseek-ai/dsh");
    console.error("");
    console.error("Or set DSH_BIN to point at the dsh binary.");
    process.exit(1);
  }

  log(`Found dsh at: ${dsh}`);

  // Set up app home
  const dataDir = getDataDir();
  const home = path.join(dataDir, "home");
  const logsDir = path.join(home, "logs");
  fs.mkdirSync(logsDir, { recursive: true });
  const logFile = path.join(logsDir, `sidecar-${Date.now()}.log`);

  log(`App home: ${home}`);

  // Launch sidecar
  const env = { ...process.env, DSH_HOME: home };
  const dshDir = path.dirname(dsh);
  env.PATH = dshDir + ";" + env.PATH;

  const args = ["web", "--no-open", "--port", "0"];
  const sidecar = spawn(dsh, args, {
    env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  log(`Sidecar PID: ${sidecar.pid}`);

  const outputLines = [];
  let sidecarUrl = null;

  sidecar.stdout.on("data", (chunk) => {
    const text = chunk.toString();
    outputLines.push(text);
    fs.appendFileSync(logFile, text);
    if (!sidecarUrl) {
      const url = extractUrlFromOutput(outputLines);
      if (url) {
        sidecarUrl = url;
        log(`dsh web ready at: ${url}`);
      }
    }
  });

  sidecar.stderr.on("data", (chunk) => {
    fs.appendFileSync(logFile, chunk.toString());
  });

  sidecar.on("close", (code) => {
    log(`Sidecar exited with code ${code}`);
    if (sidecarUrl) {
      // Try to open browser
      require("child_process").exec(`start "" "${sidecarUrl}"`, { windowsHide: true });
    }
    process.exit(code || 0);
  });

  // Wait for sidecar URL
  if (!sidecarUrl) {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`dsh web did not print URL within 90 seconds`));
      }, 90_000);
      const poll = setInterval(() => {
        if (sidecarUrl) {
          clearInterval(poll);
          clearTimeout(timer);
          resolve();
        }
      }, 500);
    });
  }

  // Verify HTTP
  await waitForHttp(sidecarUrl, 30_000);
  log(`UI ready: ${sidecarUrl}`);

  // Open browser
  require("child_process").exec(`start "" "${sidecarUrl}"`, { windowsHide: true });

  // Keep alive until sidecar exits
  log("Press Ctrl+C to stop");
}

main().catch((err) => {
  console.error("Fatal error:", err.message);
  process.exit(1);
});
