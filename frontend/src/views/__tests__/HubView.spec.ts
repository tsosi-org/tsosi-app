import { flushPromises, type VueWrapper } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"

import { hubBackend } from "@/__tests__/hub-backend"
import { ORG } from "@/__tests__/hub-fixtures"
import { mountComponent } from "@/__tests__/mount"
import EntityMeta from "@/components/EntityMeta.vue"
import { loadSession } from "@/singletons/hub-session"
import HubView from "@/views/HubView.vue"

const DATA_INFO = "To consider before reading the data"

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

describe("HubView public page tab", () => {
  it("shows the profile without the box about the data below", async () => {
    hubBackend()
    await loadSession(true)
    const mounted = await mountComponent(HubView, {
      route: "/hub/T123456?tab=page",
      stubs: { HubSupports: true },
    })
    wrapper = mounted.wrapper as VueWrapper
    await flushPromises()
    const page = wrapper.find("section.profile")
    expect(page.exists()).toBe(true)
    expect(page.findComponent(EntityMeta).exists()).toBe(true)
    expect(page.text()).not.toContain(DATA_INFO)
  })

  it("keeps the box on the public page", async () => {
    const mounted = await mountComponent(EntityMeta, {
      props: { entity: ORG },
    })
    wrapper = mounted.wrapper as VueWrapper
    expect(wrapper.text()).toContain(DATA_INFO)
  })
})
