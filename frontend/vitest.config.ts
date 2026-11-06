import { defineConfig, mergeConfig } from "vitest/config"

import viteConfig from "./vite.config"

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      include: ["src/**/__tests__/*.spec.ts"],
      setupFiles: ["src/__tests__/setup.ts"],
      env: { VITE_API_ROOT: "/api" },
      coverage: { include: ["src/**/*.{ts,vue}"] },
      // A runaway test (e.g. an endless reactive loop, which the test
      // timeout can't stop) crashes its worker at 1 GB instead of growing to
      // Node's default heap limit (~4 GB) and freezing the machine. A worker
      // peaks at ~0.5 GB on the Hub's specs.
      execArgv: ["--max-old-space-size=1024"],
      maxWorkers: 4,
    },
  }),
)
