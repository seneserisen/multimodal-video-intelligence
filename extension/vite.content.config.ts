import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/content-script/index.ts"),
      formats: ["iife"],
      name: "VideoIntelligenceContentScript",
      fileName: () => "content-script.js",
    },
  },
});
