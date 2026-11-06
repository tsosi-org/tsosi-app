import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import { mockApi, type MockRequest } from "@/__tests__/api-mock"
import { ARXIV, COUPERIN, DOAJ, entity } from "@/__tests__/hub-fixtures"
import { mountComponent } from "@/__tests__/mount"
import SearchBar from "@/components/SearchBar.vue"

// The search waits for the typing to pause
const DEBOUNCE = 260

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

async function mountSearch(props: Record<string, unknown> = {}) {
  const mounted = await mountComponent(SearchBar, { props })
  wrapper = mounted.wrapper as VueWrapper
  return mounted
}

async function type(text: string) {
  const input = wrapper!.find("input")
  await input.trigger("focus")
  await input.setValue(text)
  await wait(DEBOUNCE)
  await flushPromises()
}

function key(name: string) {
  return wrapper!.find("input").trigger("keydown", { key: name })
}

// The results, teleported with the popover
function results(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>(".search-result")]
}

function resultTexts(): string[] {
  return results().map((r) => r.textContent!.replace(/\s+/g, " ").trim())
}

function groupTitles(): string[] {
  return [...document.querySelectorAll(".search-category-title")].map((t) =>
    t.textContent!.trim(),
  )
}

function organizations(
  body: object | ((request: MockRequest) => object),
  status = 200,
) {
  return mockApi({
    "hub/organizations": (request) => ({
      status,
      body: typeof body == "function" ? body(request) : body,
    }),
  })
}

describe("SearchBar in the Hub", () => {
  it("picks an organization among the results, in one list", async () => {
    const requests = organizations({ results: [COUPERIN, DOAJ], lookup: null })
    await mountSearch({ hub: true })
    await type("op")
    expect(requests[0].params.get("search")).toBe("op")
    // Not grouped by role: in the order of the results, then the option
    // adding one
    expect(groupTitles()).toEqual([])
    expect(resultTexts()).toEqual([
      "Couperin",
      "DOAJ",
      "Not found? Add an organization",
    ])
    results()[1].click()
    expect(wrapper!.emitted("select")).toEqual([
      [expect.objectContaining({ id: DOAJ.id })],
    ])
    // Reset after the pick
    await flushPromises()
    expect(results()).toEqual([])
    expect((wrapper!.find("input").element as HTMLInputElement).value).toBe("")
  })

  it("waits for two characters", async () => {
    const requests = organizations({ results: [], lookup: null })
    await mountSearch({ hub: true })
    await type("o")
    expect(requests).toEqual([])
    expect(results()).toEqual([])
  })

  it("adds an organization missing from TSOSI from the text searched", async () => {
    // The record of an ID missing from TSOSI is looked up by the panel adding
    // it, not offered here
    organizations({
      results: [],
      lookup: {
        registry: "ror",
        identifier: "02feahw73",
        record: { registry: "ror", identifier: "02feahw73", name: "CNRS" },
        error: null,
      },
    })
    await mountSearch({ hub: true, addLabel: "Add an infrastructure" })
    await type("02feahw73")
    expect(resultTexts()).toEqual(["Not found? Add an infrastructure"])
    results()[0].click()
    expect(wrapper!.emitted("add")).toEqual([["02feahw73"]])
    expect(wrapper!.emitted()).not.toHaveProperty("addRecord")
  })

  it("shows the errors, which can't be picked", async () => {
    organizations({}, 500)
    await mountSearch({ hub: true })
    await type("arxiv")
    expect(resultTexts()).toEqual([
      "The search failed. Please try again.",
      "Not found? Add an organization",
    ])
    results()[0].click()
    // Still open, nothing picked
    expect(results()).toHaveLength(2)
    expect(wrapper!.emitted()).not.toHaveProperty("select")
    expect(wrapper!.emitted()).not.toHaveProperty("add")
  })

  it("is used with the keyboard", async () => {
    organizations({ results: [DOAJ, ARXIV], lookup: null })
    await mountSearch({ hub: true })
    await type("ar")
    await key("ArrowDown")
    await key("ArrowDown")
    await key("ArrowDown")
    await key("ArrowUp")
    const highlighted = document.querySelector(".search-result.highlighted")
    expect(highlighted?.textContent).toContain("arXiv")
    expect(highlighted?.getAttribute("aria-selected")).toBe("true")
    await key("Enter")
    expect(wrapper!.emitted("select")).toEqual([
      [expect.objectContaining({ id: ARXIV.id })],
    ])
  })

  it("closes on Escape and when leaving it", async () => {
    organizations({ results: [DOAJ], lookup: null })
    await mountSearch({ hub: true })
    await type("doaj")
    expect(results()).toHaveLength(2)
    await key("Escape")
    await flushPromises()
    expect(results()).toEqual([])

    await wrapper!.find("input").trigger("focus")
    await flushPromises()
    expect(results()).toHaveLength(2)
    await wrapper!.find("input").trigger("focusout")
    await flushPromises()
    expect(results()).toEqual([])
  })

  it("shows the results of the last query only", async () => {
    // The first query's response arrives last
    const responses: Record<string, number> = { slow: 500, fast: 0 }
    mockApi({
      "hub/organizations": (request) => {
        const query = request.params.get("search")!
        return {
          body: {
            results: [entity({ id: query, name: `Result ${query}` })],
            lookup: null,
          },
        }
      },
    })
    const fetchMock = (await import("vitest")).vi.mocked(fetch)
    const respond = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => {
      const query = new URL(
        String(input),
        window.location.href,
      ).searchParams.get("search")!
      await wait(responses[query] ?? 0)
      return respond(input, init)
    })
    await mountSearch({ hub: true })
    const input = wrapper!.find("input")
    await input.trigger("focus")
    await input.setValue("slow")
    await wait(DEBOUNCE)
    await input.setValue("fast")
    // Until the slow response arrived, after the fast one
    await wait(DEBOUNCE + 600)
    await flushPromises()
    expect(resultTexts()[0]).toContain("Result fast")
  })

  it("focuses itself when asked, e.g. to replace an organization", async () => {
    await mountSearch({ hub: true, autofocus: true })
    expect(document.activeElement).toBe(wrapper!.find("input").element)
  })
})

describe("SearchBar on the site", () => {
  function page(names: string[], next: string | null = null) {
    return {
      count: 3,
      next,
      previous: null,
      results: names.map((name) =>
        entity({
          id: name.toLowerCase().replace(" ", "-"),
          name,
          is_recipient: name.startsWith("Infra"),
        }),
      ),
    }
  }

  it("opens the page of a result, the whole entry being a link", async () => {
    const requests = mockApi({
      "entities/": { body: page(["Uni A", "Infra B"]) },
    })
    const { router } = await mountSearch()
    await type("a")
    expect(
      requests.find((r) => r.route == "entities/")!.params.get("search"),
    ).toBe("a")
    expect(groupTitles()).toEqual(["Infrastructures", "Supporters"])
    const links = [
      ...document.querySelectorAll<HTMLAnchorElement>("a.search-result"),
    ]
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "/entities/infra-b",
      "/entities/uni-a",
    ])
    // With the keyboard: Enter opens the highlighted one
    await key("ArrowDown")
    await key("Enter")
    await flushPromises()
    expect(router.currentRoute.value.path).toBe("/entities/infra-b")
  })

  it("loads the next results once scrolled to their end", async () => {
    const nextUrl = "http://localhost/api/entities/?page=2"
    mockApi({
      "entities/": (request) => ({
        body: request.params.get("page")
          ? page(["Uni C"])
          : page(["Uni A", "Uni B"], nextUrl),
      }),
    })
    await mountSearch()
    await type("uni")
    expect(results()).toHaveLength(2)
    const list = document.querySelector<HTMLElement>(".search-results")!
    list.dispatchEvent(new Event("scroll"))
    await flushPromises()
    expect(resultTexts().map((t) => t.replace(/\s/g, ""))).toEqual([
      "UniA",
      "UniB",
      "UniC",
    ])
  })
})
