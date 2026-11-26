import { execSync } from "node:child_process"
import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

/**
 * This basic function is used to split the app code into
 * separate chunks. I tried to separate heavy code that is
 * component specific and not required througout the whole app.
 * The goal is to lighten the individual chunk size.
 *
 * @param id The ID of the module being processed.
 * @returns The name of the output chunk. If `undefined`, it will  be appended
 *          to the default chunk `index-{hash}.js`.
 */
function manualChunks(id: string): string | undefined {
  if (id.includes("leaflet")) {
    return "leaflet"
  }
  if (id.includes("chart.js") || id.includes("chartjs")) {
    return "chart-js"
  }
  // Loaded after the app starts, cf. utils/error-tracking.ts
  if (id.includes("@sentry") || id.includes("web-vitals")) {
    return "error-tracking"
  }
  if (id.includes("primevue/datatable")) {
    return "vendor-datatable"
  }
  if (id.includes("node_modules")) {
    return "vendors"
  }
  return undefined
}

/**
 * The built commit, the release of the errors sent to GlitchTip, as the
 * backend's (`read_release`, from the `deployment.json` of the build).
 */
function gitRelease(): string {
  try {
    return execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim()
      .slice(0, 12)
  } catch {
    return ""
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  define: {
    "import.meta.env.VITE_RELEASE": JSON.stringify(gitRelease()),
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    // The API and the media on the same origin, as by nginx in production
    // (the Hub's session cookies, the images of the newsletters)
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
      "/media": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: manualChunks,
      },
    },
  },
})
