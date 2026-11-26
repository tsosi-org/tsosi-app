import type { App } from "vue"

/**
 * Error tracking: the errors of the visitors' browsers are sent to the
 * team's GlitchTip.
 */
export function initErrorTracking(app: App): void {
  const dsn = import.meta.env.VITE_MONITORING_DSN
  if (!dsn) {
    return
  }
  import("@/utils/error-tracking-sdk")
    .then((Sentry) => {
      Sentry.init({
        app,
        dsn,
        tunnel: import.meta.env.VITE_MONITORING_TUNNEL,
        environment:
          import.meta.env.VITE_MONITORING_ENVIRONMENT ?? import.meta.env.MODE,
        release: import.meta.env.VITE_RELEASE || undefined,
        dataCollection: { userInfo: false, cookies: false },
        integrations: (defaults) =>
          defaults.filter(
            (integration) => integration.name !== "BrowserSession",
          ),
        ignoreErrors: [
          // Harmless browser notices
          "ResizeObserver loop limit exceeded",
          "ResizeObserver loop completed with undelivered notifications",
        ],
        // Errors of browser extensions and other scripts than the app's
        allowUrls: [window.location.origin],
        beforeSend: (event) => {
          if (event.request?.url) {
            event.request.url = scrubUrl(event.request.url)
          }
          return event
        },
        beforeBreadcrumb: (breadcrumb) => {
          // Navigations (`from`, `to`) and requests (`url`)
          const data = breadcrumb.data
          if (data) {
            for (const key of ["from", "to", "url"]) {
              if (typeof data[key] == "string") {
                data[key] = scrubUrl(data[key])
              }
            }
          }
          return breadcrumb
        },
      })
    })
    .catch(() => {
      // Monitoring must never break the app
    })
}

/**
 * The URL without the value of its `token` parameter, in the query or the
 * fragment, e.g. the Hub's login links.
 */
export function scrubUrl(url: string): string {
  return url.replace(/([?#&]token=)[^&#]*/g, "$1[Filtered]")
}
