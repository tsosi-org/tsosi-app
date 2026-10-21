/**
 * Setup of the unit tests: no request leaves the tests. The API is mocked
 * per test with `mockApi`; the reference data loaded at startup, when
 * `ref-data` is imported, has the currencies below only.
 */
import { afterEach, vi } from "vitest"

import { mockApi, resetApiMock } from "./api-mock"

vi.stubGlobal("fetch", vi.fn())
mockApi({
  "entities/all/": { body: [] },
  "static_data/country.json": { body: [] },
  "currencies/": {
    body: [
      { id: "EUR", name: "Euro" },
      { id: "GBP", name: "Pound sterling" },
      { id: "USD", name: "US dollar" },
    ],
  },
})

// Missing from jsdom, which has no layout: no media query matches
Element.prototype.scrollTo ??= () => {}
Element.prototype.scrollIntoView ??= () => {}
window.matchMedia ??= (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList

afterEach(() => {
  resetApiMock()
})
