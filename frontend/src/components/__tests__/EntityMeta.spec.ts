import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import { mockApi } from "@/__tests__/api-mock"
import { MEMBER } from "@/__tests__/hub-backend"
import { ARXIV, ORG } from "@/__tests__/hub-fixtures"
import { buttonNames, findButton, mountComponent } from "@/__tests__/mount"
import EntityMeta from "@/components/EntityMeta.vue"
import { loadSession, type Member } from "@/singletons/hub-session"
import type { EntityDetails } from "@/singletons/ref-data"

const POLICY_URL = "https://uni.edu/open-science-policy"

// Missing from jsdom: used by the description's auto-resized textarea
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver

let wrapper: VueWrapper | null = null

function unmount() {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
}

afterEach(unmount)

async function logIn(member: Member | null) {
  mockApi({ "hub/me": member ? { body: member } : { status: 403 } })
  await loadSession(true)
}

async function mountMeta(props: Record<string, unknown>) {
  const mounted = await mountComponent(EntityMeta, { props })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return mounted
}

async function startEditing() {
  findButton(wrapper!.element, "Edit")!.click()
  await flushPromises()
}

function hasInput(label: string): boolean {
  return wrapper!.find(`input[aria-label="${label}"]`).exists()
}

const INFRASTRUCTURE: EntityDetails = { ...ARXIV, children: [] }

describe("EntityMeta", () => {
  it("links to the Hub instead of editing, on the public page", async () => {
    await logIn(MEMBER)
    const { router } = await mountMeta({
      entity: ORG,
      hubLink: {
        name: "hub-home",
        params: { entityId: "T123456" },
        query: { tab: "page" },
      },
    })
    const link = wrapper!.find(".edit-bar a")
    expect(link.text()).toBe("Edit in the Hub")
    expect(link.attributes("href")).toBe("/hub/T123456?tab=page")
    expect(findButton(wrapper!.element, "Edit")).toBeUndefined()
    expect(router.currentRoute.value.path).toBe("/")
  })

  it("has no edit bar without the rights", async () => {
    await logIn(null)
    await mountMeta({ entity: ORG })
    expect(wrapper!.find(".edit-bar").exists()).toBe(false)
  })

  it("hides the icon from the members, not from the TSOSI team", async () => {
    await logIn(MEMBER)
    await mountMeta({ entity: ORG, editable: true })
    await startEditing()
    expect(hasInput("Logo")).toBe(true)
    expect(hasInput("Icon")).toBe(false)
    unmount()

    await logIn({ ...MEMBER, is_staff: true, organization: null })
    await mountMeta({ entity: ORG, editable: true })
    await startEditing()
    expect(hasInput("Icon")).toBe(true)
  })

  it("shows the open science policy of an institution", async () => {
    await logIn(MEMBER)
    await mountMeta({ entity: { ...ORG, open_science_policy_url: POLICY_URL } })
    const link = wrapper!
      .findAll("a")
      .find((a) => a.text() == "Open science policy")
    expect(link?.attributes("href")).toBe(POLICY_URL)
    unmount()

    await mountMeta({ entity: ORG })
    expect(wrapper!.text()).not.toContain("Open science policy")
  })

  it("edits the open science policy of an institution only", async () => {
    await logIn(MEMBER)
    await mountMeta({
      entity: { ...ORG, open_science_policy_url: POLICY_URL },
      editable: true,
    })
    await startEditing()
    const input = wrapper!.find<HTMLInputElement>(
      'input[aria-label="Open science policy URL"]',
    )
    expect(input.element.value).toBe(POLICY_URL)
    expect(buttonNames(wrapper!.element)).toContain("Save")
    unmount()

    await logIn({ ...MEMBER, is_staff: true, organization: null })
    await mountMeta({ entity: INFRASTRUCTURE, editable: true })
    await startEditing()
    expect(hasInput("Open science policy URL")).toBe(false)
    expect(hasInput("Support page URL")).toBe(true)
  })

  it("sends the open science policy with the edits", async () => {
    await logIn(MEMBER)
    await mountMeta({ entity: ORG, editable: true })
    await startEditing()
    const requests = mockApi({
      [`entities/${ORG.id}/edit/`]: { body: ORG },
    })
    await wrapper!
      .find('input[aria-label="Open science policy URL"]')
      .setValue(POLICY_URL)
    findButton(wrapper!.element, "Save")!.click()
    await flushPromises()
    expect(requests.at(-1)).toMatchObject({
      method: "PATCH",
      body: { open_science_policy_url: POLICY_URL },
    })
    expect(requests.at(-1)!.body).not.toHaveProperty("infrastructure")
  })
})
