import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import { mockApi, type MockResponse } from "@/__tests__/api-mock"
import { ARXIV, entity, ORG } from "@/__tests__/hub-fixtures"
import { findButton, mountComponent } from "@/__tests__/mount"
import NewOrganizationPanel from "@/components/hub/NewOrganizationPanel.vue"

// The lookup waits for the typing to pause
const DEBOUNCE = 410

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

const ADD_ROUTE = `hub/entities/${ORG.id}/organizations`

const CNRS_RECORD = {
  registry: "ror",
  identifier: "02feahw73",
  name: "CNRS",
  country: "FR",
  website: null,
}

function lookupBody(values: object = {}) {
  return {
    results: [],
    lookup: {
      registry: "ror",
      identifier: "02feahw73",
      record: CNRS_RECORD,
      error: null,
      ...values,
    },
  }
}

async function mountPanel(
  initialName: string,
  field: "agents" | "recipient" = "recipient",
) {
  const mounted = await mountComponent(NewOrganizationPanel, {
    props: { organizationId: ORG.id, field, initialName },
  })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return wrapper
}

function api(
  search: MockResponse,
  add: MockResponse = { status: 201, body: {} },
) {
  return mockApi({ "hub/organizations": search, [ADD_ROUTE]: add })
}

function submit() {
  return findButton(wrapper!.element, /^(Add|Pick)/)!
}

async function clickSubmit() {
  submit().click()
  await flushPromises()
}

function text(): string {
  return wrapper!.text().replace(/\s+/g, " ")
}

function posts(requests: { method: string }[]) {
  return requests.filter((r) => r.method == "POST")
}

describe("NewOrganizationPanel", () => {
  it("is titled after the cell it adds for", async () => {
    api({ body: { results: [], lookup: null } })
    await mountPanel("New lab", "recipient")
    const title = wrapper!.find("h4")
    expect(title.text().replace(/\s+/g, " ")).toBe(
      "Add an infrastructure Enter name, ROR ID or Wikidata ID",
    )
    // The input is labelled by it
    expect(wrapper!.find("input").attributes("aria-labelledby")).toBe(
      title.attributes("id"),
    )
    wrapper!.unmount()
    await mountPanel("New lab", "agents")
    expect(wrapper!.find("h4").text()).toMatch(/^Add an intermediary /)
  })

  it("adds an organization from its name", async () => {
    const added = entity({ id: "new-lab", name: "New lab", is_new: true })
    const requests = api(
      { body: { results: [], lookup: null } },
      { status: 201, body: added },
    )
    await mountPanel("New lab")
    // A name isn't looked up
    expect(requests).toEqual([])
    expect(submit().textContent!.trim()).toBe("Add from its name")
    await clickSubmit()
    expect(posts(requests)).toMatchObject([
      { route: ADD_ROUTE, body: { name: "New lab" } },
    ])
    expect(wrapper!.emitted("added")).toEqual([
      [expect.objectContaining({ id: "new-lab" })],
    ])
  })

  it("shows the error of the name", async () => {
    api(
      { body: { results: [], lookup: null } },
      { status: 400, body: { name: ["Enter the organization's name."] } },
    )
    await mountPanel("   ")
    await clickSubmit()
    // Checked before sending
    expect(text()).toContain(
      "Enter the organization's ROR or Wikidata ID, or its name.",
    )
    await wrapper!.find("input").setValue("x")
    await clickSubmit()
    expect(text()).toContain("Enter the organization's name.")
    expect(wrapper!.emitted()).not.toHaveProperty("added")
  })

  it.each(["02feahw73", "https://ror.org/02feahw73/"])(
    "adds an organization from its ROR record: %s",
    async (typed) => {
      const added = entity({ id: "cnrs", name: "CNRS", is_new: true })
      const requests = api({ body: lookupBody() }, { status: 201, body: added })
      await mountPanel(typed)
      expect(requests[0].params.get("search")).toBe("02feahw73")
      expect(text()).toContain("ROR record: CNRS · FR")
      expect(submit().textContent!.trim()).toBe("Add from ROR")
      await clickSubmit()
      expect(posts(requests)).toMatchObject([
        { route: ADD_ROUTE, body: { identifier: typed } },
      ])
      expect(wrapper!.emitted("added")).toEqual([
        [expect.objectContaining({ id: "cnrs" })],
      ])
    },
  )

  it("looks up the ID once typed", async () => {
    const requests = api({ body: lookupBody() })
    await mountPanel("CNRS")
    expect(submit().textContent!.trim()).toBe("Add from its name")
    await wrapper!.find("input").setValue("02feahw73")
    // Not submitted before the lookup
    expect(text()).toContain("Looking up the ROR ID…")
    expect(submit().disabled).toBe(true)
    await wait(DEBOUNCE)
    await flushPromises()
    expect(requests).toHaveLength(1)
    expect(text()).toContain("ROR record: CNRS")
    expect(submit().disabled).toBe(false)
  })

  it("picks the organization already in TSOSI with the ID", async () => {
    const existing = entity({
      ...ARXIV,
      identifiers: [{ registry: "wikidata", value: "Q118398" }],
    })
    const requests = api({ body: { results: [existing], lookup: null } })
    await mountPanel("q118398")
    expect(requests[0].params.get("search")).toBe("Q118398")
    expect(text()).toContain("Already in TSOSI: arXiv")
    expect(submit().textContent!.trim()).toBe("Pick this organization")
    await clickSubmit()
    expect(posts(requests)).toEqual([])
    expect(wrapper!.emitted("added")).toEqual([
      [expect.objectContaining({ id: ARXIV.id })],
    ])
  })

  it("shows the lookup error, which blocks the addition", async () => {
    const requests = api({
      body: lookupBody({ record: null, error: "No ROR record has this ID." }),
    })
    await mountPanel("02feahw73")
    expect(text()).toContain("No ROR record has this ID.")
    await clickSubmit()
    expect(posts(requests)).toEqual([])
    expect(wrapper!.emitted()).not.toHaveProperty("added")
  })

  it("cancels", async () => {
    api({ body: { results: [], lookup: null } })
    await mountPanel("New lab")
    findButton(wrapper!.element, "Cancel")!.click()
    expect(wrapper!.emitted("cancel")).toHaveLength(1)
  })
})
