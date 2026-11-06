import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import {
  changes,
  draftsHash,
  hubBackend,
  MEMBER,
  type HubBackend,
} from "@/__tests__/hub-backend"
import {
  ARXIV,
  DOAJ,
  declaration,
  entity,
  newSupport,
  transfer,
} from "@/__tests__/hub-fixtures"
import { findButton, mountComponent } from "@/__tests__/mount"
import { loadSession } from "@/singletons/hub-session"
import type { PreviewTransfer } from "@/singletons/ref-data"
import HubSubmitView from "@/views/HubSubmitView.vue"

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

async function mountSubmit(backend: HubBackend, route = "/hub/T123456/submit") {
  await loadSession(true)
  const mounted = await mountComponent(HubSubmitView, {
    route,
    stubs: { EntityMeta: true },
  })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return mounted
}

function text(selector: string): string[] {
  return [...wrapper!.element.querySelectorAll(selector)].map((e) =>
    e.textContent!.replace(/\s+/g, " ").trim(),
  )
}

function previewTransfer(values: Partial<PreviewTransfer>): PreviewTransfer {
  return { ...transfer(values), unconverted: false, ...values }
}

// An organization added in the Hub, without published support yet
const NEW_INFRA = entity({
  id: "new-infra",
  name: "New infrastructure",
  is_recipient: true,
  scope: null,
  is_new: true,
  is_public: false,
})

function backendWithChanges() {
  return hubBackend({
    transfers: [transfer(), transfer({ id: "t2" })],
    declarations: [
      declaration({ id: 1 }),
      declaration({ id: 2, transfer_id: "t2" }),
      newSupport({ id: 3, recipient_id: NEW_INFRA.id }),
      declaration({ id: 4, kind: "removal", status: "submitted" }),
    ],
    preview: {
      transfers: [
        previewTransfer({ id: "t1" }),
        previewTransfer({ id: "t2", recipient_id: ARXIV.id }),
        // Hidden on the public page: the API leaves its amount out (F23),
        // and the preview doesn't show it either
        previewTransfer({ id: "t3", amount_hidden: true }),
      ],
      changes: { t1: ["confirmation"], t2: ["confirmation"] },
    },
    submissions: [],
  })
}

describe("HubSubmitView", () => {
  it("counts the changes not submitted yet", async () => {
    const backend = backendWithChanges()
    backend.declarations.push(
      declaration({ id: 5, kind: "edit", transfer_id: "t3" }),
    )
    // The organization added, as the declarations' entities
    const { ENTITIES } = await import("@/__tests__/hub-fixtures")
    ENTITIES[NEW_INFRA.id] = NEW_INFRA
    try {
      await mountSubmit(backend)
      expect(text(".counts li")).toEqual([
        "1 new support",
        "2 confirmations",
        "1 edit",
        "1 new organization",
      ])
    } finally {
      delete ENTITIES[NEW_INFRA.id]
    }
  })

  it("previews the public page as it will show", async () => {
    const backend = backendWithChanges()
    // Edited: in its own currency until converted by TSOSI
    backend.preview!.transfers[1] = previewTransfer({
      id: "t2",
      recipient_id: ARXIV.id,
      amount: 700,
      currency: "USD",
      amounts_clc: undefined,
      unconverted: true,
    })
    await mountSubmit(backend)
    const preview = wrapper!.element.querySelector(".preview-frame")!
    const rows = [...preview.querySelectorAll("tbody tr")]
    expect(rows).toHaveLength(3)
    // Neither the changes nor a message: the public page only
    expect(preview.querySelector("thead")!.textContent).not.toContain("Change")
    expect(rows.map((r) => r.className).join(" ")).not.toContain("changed")
    expect(preview.querySelector(".p-message, .hint")).toBeNull()
    const texts = rows.map((r) => r.textContent!)
    // In the selected currency, the others' next to their amount
    expect(texts.filter((t) => /1\s000\s*$/.test(t))).toHaveLength(1)
    expect(texts.filter((t) => /700\sUSD/.test(t))).toHaveLength(1)
    // The hidden amount isn't shown
    expect(texts.filter((t) => t.includes("hidden"))).toHaveLength(1)
  })

  it("submits the changes previewed, with the consent", async () => {
    const backend = backendWithChanges()
    const { router } = await mountSubmit(backend)
    const hash = draftsHash(backend.declarations.slice(0, 3))
    const submit = findButton(wrapper!.element, "Submit for review")!
    expect(submit.disabled).toBe(true)
    await wrapper!.find("#hub-consent").setValue(true)
    expect(submit.disabled).toBe(false)
    submit.click()
    await flushPromises()
    expect(changes(backend)).toEqual(["POST submissions"])
    expect(backend.requests.at(-1)!.body).toEqual({
      consent: true,
      declaration_ids: [1, 2, 3],
      declarations_hash: hash,
    })
    // Back to the supports table
    expect(router.currentRoute.value.fullPath).toBe("/hub/T123456")
  })

  it("tells why the submission failed", async () => {
    const backend = backendWithChanges()
    await mountSubmit(backend)
    // Another member added a change since the preview
    backend.declarations.push(newSupport({ id: 9, recipient_id: DOAJ.id }))
    await wrapper!.find("#hub-consent").setValue(true)
    findButton(wrapper!.element, "Submit for review")!.click()
    await flushPromises()
    expect(text(".submit-box .p-message")).toEqual([
      "The changes changed since the preview.",
    ])
  })

  it("tells when a change previewed was edited since (C2)", async () => {
    const backend = backendWithChanges()
    await mountSubmit(backend)
    // Another member edited a draft previewed: same IDs, other values
    backend.declarations[0] = declaration({ id: 1, kind: "edit", amount: 9 })
    await wrapper!.find("#hub-consent").setValue(true)
    findButton(wrapper!.element, "Submit for review")!.click()
    await flushPromises()
    expect(text(".submit-box .p-message")).toEqual([
      "The changes changed since the preview.",
    ])
    expect(backend.submissions).toEqual([])
  })

  it("lists only the changes previewed, those submitted (C11)", async () => {
    const backend = backendWithChanges()
    // Another member undid a change after the list, before the preview
    backend.beforeRequest = (request) => {
      if (request.route.endsWith("/publication-preview")) {
        backend.declarations.splice(2, 1)
        backend.beforeRequest = null
      }
    }
    await mountSubmit(backend)
    // The new support isn't listed, nor submitted
    expect(text(".counts li")).toEqual(["2 confirmations"])
    await wrapper!.find("#hub-consent").setValue(true)
    findButton(wrapper!.element, "Submit for review")!.click()
    await flushPromises()
    expect(backend.requests.at(-1)!.body).toMatchObject({
      declaration_ids: [1, 2],
    })
    expect(backend.submissions).toHaveLength(1)
  })

  it("reloads when a change previewed isn't listed (C11)", async () => {
    const backend = backendWithChanges()
    // Another member saved a change after the list, before the preview
    backend.beforeRequest = (request) => {
      if (request.route.endsWith("/publication-preview")) {
        backend.declarations.push(
          declaration({ id: 9, kind: "removal", transfer_id: "t2" }),
        )
        backend.beforeRequest = null
      }
    }
    await mountSubmit(backend)
    expect(text(".p-message")).toEqual([
      "The changes were modified while the preview was loading, e.g. by another member: reload it to see and submit them. Reload",
    ])
    // Neither the changes nor their submission
    expect(wrapper!.find(".counts").exists()).toBe(false)
    expect(wrapper!.find(".submit-box").exists()).toBe(false)
    expect(wrapper!.find(".preview-frame").exists()).toBe(false)
    findButton(wrapper!.element, "Reload")!.click()
    await flushPromises()
    expect(text(".counts li")).toEqual([
      "1 new support",
      "2 confirmations",
      "1 removal",
    ])
    expect(wrapper!.find(".submit-box").exists()).toBe(true)
  })

  it("redirects to the URL with the TSOSI ID", async () => {
    const { router } = await mountSubmit(
      backendWithChanges(),
      "/hub/org/submit",
    )
    expect(router.currentRoute.value.fullPath).toBe("/hub/T123456/submit")
    await flushPromises()
    expect(text("h1")).toEqual(["Preview and submit"])
  })

  it("tells when there's nothing to submit", async () => {
    await mountSubmit(hubBackend({ transfers: [transfer()] }))
    expect(wrapper!.text()).toContain("There are no changes to submit.")
    expect(wrapper!.find(".submit-box").exists()).toBe(false)
  })

  it("is read-only for the TSOSI team", async () => {
    const backend = backendWithChanges()
    backend.member = {
      email: "admin@tsosi.org",
      is_staff: true,
      organization: null,
      can_declare_supports: false,
    }
    await mountSubmit(backend)
    expect(wrapper!.find(".submit-box").exists()).toBe(false)
    expect(wrapper!.text()).toContain(
      "You're viewing this organization's changes as a TSOSI admin, in read-only mode.",
    )
    expect(text(".counts li")).toContain("2 confirmations")
  })

  it("isn't for the members without the declaration of supports", async () => {
    const backend = backendWithChanges()
    backend.member = { ...MEMBER, can_declare_supports: false }
    await mountSubmit(backend)
    expect(text("h1")).toEqual(["404 - Not found"])
    expect(wrapper!.find(".submit-box").exists()).toBe(false)
  })
})
