/**
 * A mock of the TSOSI API at the `fetch` level, so that the request code of
 * the singletons runs: each route (without the `/api/` prefix and the
 * query) answers with a status and a JSON body, `*` the routes not listed.
 */
import { vi } from "vitest"

export interface MockResponse {
  status?: number
  body?: unknown
}

export interface MockRequest {
  method: string
  route: string
  params: URLSearchParams
  headers: Headers
  body: unknown
}

export function mockApi(
  routes: Record<string, MockResponse | ((r: MockRequest) => MockResponse)>,
): MockRequest[] {
  const requests: MockRequest[] = []
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = new URL(String(input), window.location.href)
    const request = {
      method: init?.method ?? "GET",
      route: url.pathname.replace(/^\/api\//, ""),
      params: url.searchParams,
      headers: new Headers(init?.headers),
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    }
    requests.push(request)
    // `*` answers the other routes
    const handler = routes[request.route] ?? routes["*"]
    const response = typeof handler == "function" ? handler(request) : handler
    if (!response) {
      return new Response("{}", { status: 404 })
    }
    const status = response.status ?? 200
    // No content: a response can't have a body then
    if (status == 204) {
      return new Response(null, { status })
    }
    return new Response(JSON.stringify(response.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    })
  })
  return requests
}

export function resetApiMock() {
  vi.mocked(fetch).mockImplementation(
    async () => new Response("{}", { status: 404 }),
  )
}
