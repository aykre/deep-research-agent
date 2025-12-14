import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  return {
    plugins: [react(), tailwindcss(), replaceTurnstilePreconnect(env)],
    server: {
      proxy: {
        "/research": {
          target: "ws://localhost:8000",
          ws: true,
        },
      },
    },
  };
});

function replaceTurnstilePreconnect(env: Record<string, string>) {
  return {
    name: "conditional-html",
    transformIndexHtml(html: string) {
      return html.replace(
        "<!-- turnstile -->",
        env.VITE_USE_TURNSTILE !== "true"
          ? ""
          : '<link rel="preconnect" href="https://challenges.cloudflare.com">'
      );
    },
  };
}
