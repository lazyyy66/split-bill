import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// В разработке Mini App открывается через ngrok → Vite (5173), а /api проксируется в FastAPI (8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: [".ngrok-free.app", ".ngrok-free.dev", ".ngrok.app", ".ngrok.dev"],
    proxy: { "/api": "http://localhost:8000" },
  },
});
