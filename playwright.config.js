// Playwright — LOKÁLIS smoke (spec §3). NEM kerül a CI-be (a napi.yml tisztán Python).
// A docs/-ot HTTP-n szolgáljuk ki, mert a relatív fetch (data/...?v=...) file://-on NEM működik.
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:8000" },
  webServer: {
    // .venv/bin/python — a python nincs a PATH-on; a parancs a repo gyökeréből fut
    command: ".venv/bin/python -m http.server 8000 --directory docs",
    url: "http://localhost:8000",
    reuseExistingServer: true,
    timeout: 30000,
  },
});
