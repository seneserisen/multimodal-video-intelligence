import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "service-worker": resolve(__dirname, "src/service-worker/index.ts"),
        "side-panel": resolve(__dirname, "src/side-panel/index.html"),
        offscreen: resolve(__dirname, "src/offscreen/index.html"),
      },
      output: { entryFileNames: "[name].js" },
    },
  },
});
