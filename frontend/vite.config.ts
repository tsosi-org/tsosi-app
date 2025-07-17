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
  if (id.includes("chart.js")) {
    return "chart-js"
  }
  if (id.includes("primevue/datatable")) {
    return "vendor-datatable"
  }
  if (id.includes("node_modules")) {
    return "vendors"
  }
  return undefined
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: manualChunks,
      },
    },
  },
})
