import { resolve } from "path";
import { defineConfig } from "vite";

// Builds ONLY the background service worker as an ES module.
// Manifest V3 supports ES module service workers with "type": "module".
export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/background/service-worker.ts"),
      formats: ["es"],
      fileName: () => "service-worker.js",
    },
  },
  resolve: {
    alias: { "@lib": resolve(__dirname, "src/lib") },
  },
});
