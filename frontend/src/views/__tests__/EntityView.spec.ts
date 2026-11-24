import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it, vi } from "vitest"

import { mockApi, type MockRequest } from "@/__tests__/api-mock"
import { mountComponent } from "@/__tests__/mount"
import NotFound from "@/components/atoms/NotFound.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import EntityView from "@/views/EntityView.vue"

// The reference data, loaded once when `ref-data` is imported, holds ORG
// only: it is mocked before the imports
const { ORG } = await vi.hoisted(async () => {
  const { mockApi } = await import("@/__tests__/api-mock")
  const { ORG: org } = await import("@/__tests__/hub-fixtures")
  const ORG = {
    ...org,
    identifiers: [...org.identifiers, { registry: "ror", value: "0abcdef12" }],
  }
  mockApi({
    "entities/all/": { body: [ORG] },
    "static_data/country.json": { body: [] },
    "currencies/": { body: [] },
  })
  return { ORG }
})

const STUBS = { EntityMeta: true, EntityViz: true, EntityData: true }

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

// A merged entity is missing from the reference data: the API answers for
// its IDs with the retained entity (`fetch` follows the redirect to the
// retained entity's TSOSI ID)
async function mountEntityView(route: string) {
  const requests = mockApi({
    "entities/org": { body: ORG },
    "entities/T999999": { body: ORG },
    "transfers/all/": { body: [] },
  })
  const mounted = await mountComponent(EntityView, { route, stubs: STUBS })
  wrapper = mounted.wrapper as VueWrapper
  await flushPromises()
  return { router: mounted.router, requests }
}

function entityRequests(requests: MockRequest[]): string[] {
  return requests
    .map((r) => r.route)
    .filter((r) => r.startsWith("entities/") && r != "entities/all/")
}

describe("EntityView", () => {
  it("shows the entity of its TSOSI ID", async () => {
    const { router } = await mountEntityView("/entities/T123456")
    expect(router.currentRoute.value.fullPath).toBe("/entities/T123456")
    expect(wrapper!.findComponent(EntityMeta).props("entity")).toEqual(ORG)
  })

  it("redirects a known ID to the TSOSI ID without asking the API", async () => {
    const { router, requests } = await mountEntityView(
      "/entities/0abcdef12?tab=1",
    )
    expect(router.currentRoute.value.fullPath).toBe("/entities/T123456?tab=1")
    expect(entityRequests(requests)).toEqual([])
  })

  it("redirects the ID of a merged entity to the retained one", async () => {
    const { router, requests } = await mountEntityView("/entities/T999999#data")
    expect(entityRequests(requests)).toEqual(["entities/T999999"])
    expect(router.currentRoute.value.fullPath).toBe("/entities/T123456#data")
  })

  it("shows the not found page for an unknown ID", async () => {
    const { router } = await mountEntityView("/entities/T000000")
    expect(router.currentRoute.value.fullPath).toBe("/entities/T000000")
    expect(wrapper!.findComponent(NotFound).exists()).toBe(true)
    expect(wrapper!.findComponent(EntityMeta).exists()).toBe(false)
  })
})
