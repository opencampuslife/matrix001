import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  base: "/matrix/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/matrix/api": {
        target: "http://localhost:18080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/matrix\/api/, ""),
      },
    },
  },
});
