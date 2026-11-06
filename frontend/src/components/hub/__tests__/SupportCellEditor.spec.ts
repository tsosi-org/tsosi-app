import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"
import { reactive } from "vue"

import { mockApi } from "@/__tests__/api-mock"
import { ARXIV, COUPERIN, DOAJ, ORG } from "@/__tests__/hub-fixtures"
import { buttonNames, findButton, mountComponent } from "@/__tests__/mount"
import SupportCellEditor from "@/components/hub/SupportCellEditor.vue"
import type { SupportDraft } from "@/singletons/hub-declarations"
import { emptyDraft } from "@/utils/hub-support-rows"

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

async function mountEditor(
  field: string,
  draft: SupportDraft,
  errors: Record<string, string[]> = {},
  // Test Utils stubs the transitions, e.g. the popovers' positioning
  stubs: Record<string, boolean> = {},
) {
  const mounted = await mountComponent(SupportCellEditor, {
    props: { field, draft, errors, organizationId: ORG.id },
    stubs,
  })
  wrapper = mounted.wrapper as VueWrapper
  return wrapper
}

function draftWith(values: Partial<SupportDraft> = {}): SupportDraft {
  return reactive({ ...emptyDraft("EUR"), ...values })
}

function click(name: string) {
  const button = findButton(wrapper!.element, name)
  expect(button, name).toBeDefined()
  button!.click()
  return flushPromises()
}

async function search(text: string) {
  const input = wrapper!.find("input")
  await input.setValue(text)
  await wait(260)
  await flushPromises()
}

function pickResult(text: string) {
  const result = [
    ...document.querySelectorAll<HTMLElement>(".search-result"),
  ].find((r) => r.textContent?.includes(text))
  expect(result, text).toBeDefined()
  result!.click()
  return flushPromises()
}

describe("SupportCellEditor of an organization", () => {
  it("shows the beneficiary, replaced from the search in place", async () => {
    mockApi({
      "hub/organizations": { body: { results: [ARXIV], lookup: null } },
    })
    const draft = draftWith({ recipient: DOAJ })
    await mountEditor("recipient", draft)
    expect(wrapper!.text()).toContain("DOAJ")
    // In scope: not highlighted
    expect(wrapper!.find(".scope-highlight").exists()).toBe(false)
    expect(wrapper!.find("input").exists()).toBe(false)
    expect(buttonNames(wrapper!.element)).toEqual(["Replace"])

    await click("Replace")
    // The search, focused, with the button keeping the current one
    expect(document.activeElement).toBe(wrapper!.find("input").element)
    await click("Keep it")
    expect(wrapper!.text()).toContain("DOAJ")

    await click("Replace")
    await search("arxiv")
    await pickResult("arXiv")
    expect(draft.recipient?.id).toBe(ARXIV.id)
    expect(wrapper!.find("input").exists()).toBe(false)
  })

  it("positions the results of the search opened by Replace", async () => {
    mockApi({
      "hub/organizations": { body: { results: [ARXIV], lookup: null } },
    })
    await mountEditor(
      "recipient",
      draftWith({ recipient: DOAJ }),
      {},
      {
        transition: false,
      },
    )
    await click("Replace")
    await search("arxiv")
    // Shown before the popover's portal was rendered, they were left at the
    // bottom of the page, unpositioned
    const popover = document.querySelector<HTMLElement>(".p-popover")!
    expect(popover.style.position).toBe("absolute")
    expect(document.querySelectorAll(".search-result")).toHaveLength(2)
  })

  it("highlights a beneficiary whose supports aren't public", async () => {
    await mountEditor(
      "recipient",
      draftWith({ recipient: { ...DOAJ, scope: null } }),
    )
    const value = wrapper!.find(".organization-value")
    expect(value.classes()).toEqual(
      expect.arrayContaining(["scope-highlight", "scope-to-check"]),
    )
    // No label: the explanation is in its tooltip
    expect(value.text()).not.toContain("To be checked")
    wrapper!.unmount()
    await mountEditor(
      "recipient",
      draftWith({ recipient: { ...DOAJ, scope: "out_of_scope" } }),
    )
    expect(wrapper!.find(".organization-value").classes()).toContain(
      "scope-out-of-scope",
    )
  })

  it("doesn't highlight an intermediary", async () => {
    await mountEditor(
      "agents",
      draftWith({ agents: [{ ...COUPERIN, scope: null }] }),
    )
    expect(wrapper!.find(".scope-highlight").exists()).toBe(false)
  })

  it("searches at once without beneficiary", async () => {
    await mountEditor("recipient", draftWith())
    expect(wrapper!.find("input").attributes("placeholder")).toBe(
      "Pick the beneficiary",
    )
  })

  it("keeps one intermediary at most, or none", async () => {
    mockApi({
      "hub/organizations": { body: { results: [ARXIV], lookup: null } },
    })
    const draft = draftWith({ agents: [COUPERIN] })
    await mountEditor("agents", draft)
    expect(buttonNames(wrapper!.element)).toEqual([
      "Replace",
      "No intermediary",
    ])
    await click("Replace")
    await search("arxiv")
    await pickResult("arXiv")
    expect(draft.agents.map((a) => a.id)).toEqual([ARXIV.id])
    await click("No intermediary")
    expect(draft.agents).toEqual([])
    expect(wrapper!.find("input").attributes("placeholder")).toBe(
      "Pick the intermediary, if any",
    )
  })

  it("asks to add an infrastructure or an intermediary", async () => {
    mockApi({ "hub/organizations": { body: { results: [], lookup: null } } })
    await mountEditor("agents", draftWith())
    await search("New lab")
    await pickResult("Not found? Add an intermediary")
    expect(wrapper!.emitted("addOrganization")).toEqual([["agents", "New lab"]])

    wrapper!.unmount()
    document.body.innerHTML = ""
    await mountEditor("recipient", draftWith())
    await search("02feahw73")
    await pickResult("Not found? Add an infrastructure")
    expect(wrapper!.emitted("addOrganization")).toEqual([
      ["recipient", "02feahw73"],
    ])
  })

  it("doesn't offer the record of an ID missing from TSOSI", async () => {
    mockApi({
      "hub/organizations": {
        body: {
          results: [],
          lookup: {
            registry: "ror",
            identifier: "02feahw73",
            record: { registry: "ror", identifier: "02feahw73", name: "CNRS" },
            error: null,
          },
        },
      },
    })
    await mountEditor("recipient", draftWith())
    await search("02feahw73")
    const results = [...document.querySelectorAll(".search-result")]
    // Added from the panel under the row
    expect(results.map((r) => r.textContent?.trim())).toEqual([
      "Not found? Add an infrastructure",
    ])
  })
})

describe("SupportCellEditor of the amount", () => {
  it("commits the amount as typed, in any convention", async () => {
    const draft = draftWith({ amount: 1500.5, amountText: "1500.5" })
    await mountEditor("amount", draft)
    const input = wrapper!.find("input")
    expect((input.element as HTMLInputElement).value).toBe("1500.5")
    await input.setValue("1 234,56")
    expect(draft.amount).toBe(1234.56)
    // A trailing separator while typing (C7)
    await input.setValue("1500,")
    expect(draft.amount).toBe(1500)
    expect(draft.amountText).toBe("1500,")
    expect(input.classes()).not.toContain("p-invalid")
    // Three decimals
    await input.setValue("1,234")
    expect(draft.amount).toBe(1.234)
    // Required, but checked on save
    await input.setValue("")
    expect(draft.amount).toBeNull()
    expect(input.classes()).not.toContain("p-invalid")
  })

  it("flags an invalid amount", async () => {
    const draft = draftWith({ amount: 10, amountText: "10" })
    await mountEditor("amount", draft)
    const input = wrapper!.find("input")
    await input.setValue("12abc")
    expect(draft.amount).toBeNull()
    expect(input.classes()).toContain("p-invalid")
    // The message is listed by the panel under the row: only the currency
    expect(wrapper!.text()).toBe("EUR")
  })

  it("flags the errors of its field only", async () => {
    await mountEditor("amount", draftWith({ amountText: "0" }), {
      currency: ["Pick the currency of the amount."],
    })
    expect(wrapper!.find("input").classes()).not.toContain("p-invalid")
    await wrapper!.setProps({
      errors: { amount: ["The amount must be positive."] },
    })
    expect(wrapper!.find("input").classes()).toContain("p-invalid")
  })

  it("picks its currency next to it", async () => {
    const draft = draftWith({ currency: "EUR" })
    await mountEditor("amount", draft, {
      currency: ["Pick the currency of the amount."],
    })
    await flushPromises()
    expect(wrapper!.find(".p-select-label").text()).toBe("EUR")
    // Its own errors
    expect(wrapper!.find(".p-select").classes()).toContain("p-invalid")
    expect(wrapper!.find("input").classes()).not.toContain("p-invalid")
    await wrapper!.find(".p-select").trigger("click")
    await flushPromises()
    const options = [
      ...document.querySelectorAll<HTMLElement>(".p-select-option"),
    ]
    expect(options.map((o) => o.textContent?.trim())).toEqual([
      "EUR · Euro",
      "GBP · Pound sterling",
      "USD · US dollar",
    ])
    options[2].click()
    await flushPromises()
    expect(draft.currency).toBe("USD")
  })

  it("tells when it's being edited", async () => {
    await mountEditor("amount", draftWith())
    await wrapper!.find("input").trigger("focusin")
    expect(wrapper!.emitted("focus")).toHaveLength(1)
  })
})
