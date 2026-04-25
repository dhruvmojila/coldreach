import { resolve } from "path";
import { defineConfig } from "vite";

// Builds ONLY the content script as IIFE.
// Service worker is built by vite.sw.config.ts.
// Run AFTER vite.popup.config.ts so emptyOutDir:false preserves popup build.
export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/content/index.ts"),
      formats: ["iife"],
      name: "ColdReachContent",
      fileName: () => "content.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  resolve: {
    alias: { "@lib": resolve(__dirname, "src/lib") },
  },
});
