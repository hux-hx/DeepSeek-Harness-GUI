"use strict";
/**
 * DeepSeek Harness Desktop — Electron main process.
 *
 * Spawns `dsh web` as a supervised sidecar on an OS-picked port, waits for
 * the UI to become reachable, then opens it in a native window. The sidecar
 * is terminated when the window closes.
 */
const { app, BrowserWindow, Tray, Menu, shell, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");

const APP_ID = "deepseek-harness-desktop";
const APP_NAME = "DeepSeek Harness";

// ── helpers ─────────────────────────────────────────────────────────────────

function dataDir() {
  return path.join(app.getPath("appData"), "DeepSeekHarnessDesktop");
}

function findDsh() {
  // Try the bundled launcher first (installed alongside the Electron app)
  const bundled = path.join(__dirname, "..", "bin", "deepseek-harness-desktop");
  if (fs.existsSync(bundled)) return bundled;
  // Try system PATH
  try {
    const cmd =
      process.platform === "win32" ? "where dsh" : "command -v dsh";
    const where = require("child_process")
      .execSync(cmd, { encoding: "utf8" })
      .trim()
      .split(/\r?\n/)[0];
    if (where && fs.existsSync(where)) return where;
  } catch {}
  return null;
}

function waitForHttp(url, timeoutMs = 90_000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    function check() {
      http
        .get(url, (res) => {
          if (res.statusCode === 200) resolve(url);
          else setTimeout(check, 300);
        })
        .on("error", () => {
          if (Date.now() < deadline) setTimeout(check, 300);
          else reject(new Error(`dsh web did not become ready within ${timeoutMs / 1000}s`));
        });
    }
    check();
  });
}

function extractUrlFromSidecar(outputLines) {
  for (const line of outputLines) {
    const m = line.match(/dsh web:\s*(\S+)/);
    if (m) return m[1];
  }
  return null;
}

// ── sidecar lifecycle ────────────────────────────────────────────────────────

let sidecar = null;
let sidecarUrl = null;
let sidecarLogLines = [];

function startSidecar(dshPath) {
  const home = path.join(dataDir(), "home");
  const logsDir = path.join(home, "logs");
  fs.mkdirSync(logsDir, { recursive: true });
  const logFile = path.join(logsDir, `sidecar-${Date.now()}.log`);

  const env = { ...process.env, DSH_HOME: home };
  const dshDir = path.dirname(dshPath);
  env.PATH = dshDir + (process.platform === "win32" ? ";" : ":") + env.PATH;

  const args = ["web", "--no-open", "--port", "0"];
  sidecar = spawn(dshPath, args, {
    env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: process.platform === "win32",
  });

  sidecar.stdout.on("data", (chunk) => {
    const text = chunk.toString();
    sidecarLogLines.push(text);
    fs.appendFileSync(logFile, text);
    if (!sidecarUrl) {
      const url = extractUrlFromSidecar(sidecarLogLines);
      if (url) sidecarUrl = url;
    }
  });

  sidecar.stderr.on("data", (chunk) => {
    fs.appendFileSync(logFile, chunk.toString());
  });

  sidecar.on("close", (code) => {
    console.log(`sidecar exited with code ${code}`);
    sidecar = null;
  });

  return { home, logFile };
}

function killSidecar() {
  if (!sidecar) return;
  const pid = sidecar.pid;
  sidecar = null;
  sidecarUrl = null;
  if (process.platform === "win32") {
    try {
      require("child_process").execSync(`taskkill /PID ${pid} /T /F`, {
        timeout: 5000,
      });
    } catch {}
  } else {
    try {
      process.kill(-pid, "SIGTERM");
      setTimeout(() => {
        try { process.kill(-pid, "SIGKILL"); } catch {}
      }, 4000);
    } catch {}
  }
}

// ── window ───────────────────────────────────────────────────────────────────

let win = null;

function createWindow(url) {
  const iconPaths = [
    path.join(__dirname, "..", "share", "icons", "windows", "deepseek-harness-desktop.ico"),
    path.join(__dirname, "..", "share", "icons", "hicolor", "256x256", "apps", "deepseek-harness-desktop.png"),
  ];
  const icon = iconPaths.find((p) => fs.existsSync(p)) || undefined;

  win = new BrowserWindow({
    width: 1280,
    height: 832,
    minWidth: 960,
    minHeight: 600,
    title: APP_NAME,
    icon,
    trafficLightPosition: { x: 12, y: 12 },
    frame: process.platform !== "darwin",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.loadURL(url);

  win.on("closed", () => {
    win = null;
    killSidecar();
  });

  // External links → default browser
  win.webContents.setWindowOpenHandler(({ url: linkUrl }) => {
    shell.openExternal(linkUrl);
    return { action: "deny" };
  });

  return win;
}

// ── tray ─────────────────────────────────────────────────────────────────────

let tray = null;

function createTray() {
  if (process.platform === "win32") return;
  const iconPath = path.join(
    __dirname,
    "..",
    "share",
    "icons",
    "hicolor",
    "256x256",
    "apps",
    "deepseek-harness-desktop.png"
  );
  if (!fs.existsSync(iconPath)) return;
  tray = new Tray(iconPath);
  const contextMenu = Menu.buildFromTemplate([
    { label: "Show", click: () => win?.show() },
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ]);
  tray.setToolTip(APP_NAME);
  tray.setContextMenu(contextMenu);
  tray.on("click", () => win?.show());
}

// ── startup ──────────────────────────────────────────────────────────────────

async function main() {
  await app.whenReady();

  const dsh = findDsh();
  if (!dsh) {
    dialog.showErrorBox(
      "dsh not found",
      "Install DeepSeek Harness first:\n\n" +
        "Windows:  npm i -g @deepseek-ai/dsh\n" +
        "Linux:    npm i -g @deepseek-ai/dsh\n\n" +
        "Or set the DSH_BIN environment variable."
    );
    app.exit(1);
    return;
  }

  console.log(`using dsh: ${dsh}`);
  startSidecar(dsh);

  // Wait for sidecar to print its URL
  const urlTimeout = setTimeout(() => {
    if (!sidecarUrl) {
      dialog.showErrorBox(
        "Sidecar failed to start",
        "dsh web did not print its URL within 90 seconds.\n\n" +
          `Log: ${path.join(dataDir(), "home", "logs")}`
      );
      killSidecar();
      app.exit(1);
    }
  }, 90_000);

  // Poll until we have a URL, then verify HTTP
  await new Promise((resolve, reject) => {
    const poll = setInterval(() => {
      if (sidecarUrl) {
        clearInterval(poll);
        clearTimeout(urlTimeout);
        waitForHttp(sidecarUrl, 30_000)
          .then(resolve)
          .catch(reject);
      }
    }, 500);
    // Also stop polling if sidecar exits
    sidecar?.on("close", () => {
      clearInterval(poll);
      clearTimeout(urlTimeout);
      reject(new Error("dsh web exited before becoming ready"));
    });
  });

  console.log(`dsh web ready at ${sidecarUrl}`);
  createWindow(sidecarUrl);
  createTray();
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) main();
});

app.on("before-quit", () => {
  killSidecar();
});

main().catch((err) => {
  console.error(err.message);
  dialog.showErrorBox("Startup failed", err.message);
  app.exit(1);
});
