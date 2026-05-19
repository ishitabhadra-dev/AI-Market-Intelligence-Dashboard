import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "build",
    emptyOutDir: true,
    assetsDir: "static",
  },
  server: {
    port: 3001,
    strictPort: true,
  },
});
