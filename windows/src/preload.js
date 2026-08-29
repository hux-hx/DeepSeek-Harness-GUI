"use strict";
/**
 * Preload script — exposes a minimal IPC bridge between the renderer and
 * main process without exposing Node.js APIs to the web page.
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dshDesktop", {
  /** Tell the main process to quit (triggers clean sidecar shutdown). */
  quit: () => ipcRenderer.send("quit"),
  /** Whether the app is running inside Electron (vs. a browser). */
  isElectron: true,
  /** Platform string. */
  platform: process.platform,
});
