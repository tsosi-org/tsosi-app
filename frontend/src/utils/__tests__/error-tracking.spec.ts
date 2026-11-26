import { afterEach, describe, expect, it, vi } from "vitest"
import { createApp } from "vue"

const init = vi.fn()
vi.mock("@/utils/error-tracking-sdk", () => ({ init }))

import { initErrorTracking, scrubUrl } from "@/utils/error-tracking"

describe("initErrorTracking", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    init.mockClear()
  })

  it("does nothing without a DSN", async () => {
    vi.stubEnv("VITE_MONITORING_DSN", "")
    initErrorTracking(createApp({}))
    await vi.dynamicImportSettled()
    expect(init).not.toHaveBeenCalled()
  })

  it("sends no personal data nor sessions, through the tunnel", async () => {
    vi.stubEnv("VITE_MONITORING_DSN", "https://key@monitoring.example.org/2")
    vi.stubEnv("VITE_MONITORING_TUNNEL", "/api/monitoring")
    vi.stubEnv("VITE_MONITORING_ENVIRONMENT", "production")
    initErrorTracking(createApp({}))
    await vi.dynamicImportSettled()
    expect(init).toHaveBeenCalledOnce()
    const options = init.mock.calls[0][0]
    expect(options.dsn).toBe("https://key@monitoring.example.org/2")
    expect(options.tunnel).toBe("/api/monitoring")
    expect(options.environment).toBe("production")
    expect(options.dataCollection).toEqual({ userInfo: false, cookies: false })
    const event = options.beforeSend({
      request: { url: "https://tsosi.org/hub/login?next=/hub/3#token=abc.def" },
    })
    expect(event.request.url).toBe(
      "https://tsosi.org/hub/login?next=/hub/3#token=[Filtered]",
    )
    const breadcrumb = options.beforeBreadcrumb({
      data: { from: "/hub/login#token=abc", to: "/hub" },
    })
    expect(breadcrumb.data).toEqual({
      from: "/hub/login#token=[Filtered]",
      to: "/hub",
    })
    const integrations = options.integrations([
      { name: "BrowserSession" },
      { name: "GlobalHandlers" },
    ])
    expect(integrations.map((i: { name: string }) => i.name)).toEqual([
      "GlobalHandlers",
    ])
  })

  it("filters the token parameters of URLs", () => {
    expect(scrubUrl("/hub/login#token=a:b-c")).toBe(
      "/hub/login#token=[Filtered]",
    )
    expect(scrubUrl("/x?a=1&token=t&b=2")).toBe("/x?a=1&token=[Filtered]&b=2")
    expect(scrubUrl("/explore?mytoken=1")).toBe("/explore?mytoken=1")
  })
})
