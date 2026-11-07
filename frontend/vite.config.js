import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// No CDN references anywhere in this project — all dependencies are
// bundled from node_modules (installed once at `docker build` time) so the
// running app never needs to fetch anything from the internet.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,   // listen on 0.0.0.0 inside the container
    port: 5173,
    strictPort: true,
    watch: {
      // Bind-mounted volumes on some host OSes (esp. Windows/WSL, some
      // Docker Desktop setups) don't emit native file-change events —
      // polling keeps hot-reload working reliably in the field.
      usePolling: true,
    },
  },
});
