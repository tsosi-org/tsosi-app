import { flushPromises, mount, type VueWrapper } from "@vue/test-utils"
import PrimeVue from "primevue/config"
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest"

import { mockApi, type MockRequest } from "@/__tests__/api-mock"
import { MEMBER } from "@/__tests__/hub-backend"
import { findButton } from "@/__tests__/mount"
import router from "@/router"
import { loadSession } from "@/singletons/hub-session"
import HubLoginView from "@/views/HubLoginView.vue"

// A link to a filtered table of the Hub, shared by a colleague
const SHARED = "/hub/T123456?tab=page&status=pending&f_name=open%20science"

let wrapper: VueWrapper | null = null

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ""
})

// The session API: logged out until the login with the e-mail's token
function sessionBackend() {
  const backend = { loggedIn: false, requests: [] as MockRequest[] }
  backend.requests = mockApi({
    "hub/me": () => (backend.loggedIn ? { body: MEMBER } : { status: 403 }),
    "hub/login-link": { status: 204 },
    "hub/login": () => {
      backend.loggedIn = true
      return { body: MEMBER }
    },
  })
  return backend
}

// The Hub's page, loaded by the navigation after the login: slow to
// transform the first time
beforeAll(() => import("@/views/HubView.vue"), 30000)

beforeEach(async () => {
  sessionBackend()
  await loadSession(true)
})

// The login page, on the app's router (with the Hub's guards)
async function mountLogin(path: string) {
  await router.push(path)
  await router.isReady()
  wrapper = mount(HubLoginView, {
    attachTo: document.body,
    global: {
      plugins: [[PrimeVue, { theme: "none" }], router],
      stubs: { "font-awesome-icon": true },
    },
  }) as VueWrapper
  await flushPromises()
  return wrapper
}

// The navigation loads the Hub's page component: wait for it
function afterNavigation(check: () => void) {
  return vi.waitFor(check, { timeout: 2000 })
}

// The login link of the e-mail, as the backend builds it
function emailLink(next: string, token = "abc"): string {
  return `/hub/login?next=${encodeURIComponent(next).replace(/%2F/g, "/")}#token=${token}`
}

describe("a shared Hub link opened logged out", () => {
  it.each([SHARED, "/hub?tab=page&status=pending"])(
    "keeps its path and query through the login (%s)",
    async (shared) => {
      const backend = sessionBackend()

      // Redirected to the login, the link in `next`
      await router.push(shared)
      expect(router.currentRoute.value.name).toBe("hub-login")
      expect(router.currentRoute.value.query.next).toBe(shared)

      // The login link asked leads back to it
      const login = await mountLogin(router.currentRoute.value.fullPath)
      await login.find("input").setValue(MEMBER.email)
      await login.find("form").trigger("submit")
      await flushPromises()
      const linkRequest = backend.requests.find(
        (r) => r.route == "hub/login-link",
      )!
      expect(linkRequest.body).toEqual({ email: MEMBER.email, next: shared })
      login.unmount()
      wrapper = null

      // The e-mail's link, opened in a new tab: logged in, then back to it
      const fromEmail = await mountLogin(emailLink(shared))
      // The token is hidden from the URL, the `next` kept
      expect(router.currentRoute.value.hash).toBe("")
      expect(router.currentRoute.value.query.next).toBe(shared)
      findButton(fromEmail.element, "Log in")!.click()
      // `/hub` leads to the member's organization's Hub
      const expected = router.resolve(
        shared.replace(/^\/hub\?/, "/hub/T123456?"),
      )
      await afterNavigation(() => {
        const { path, query } = router.currentRoute.value
        expect({ path, query }).toEqual({
          path: expected.path,
          query: expected.query,
        })
      })
    },
  )

  it.each([
    "https://evil.org/hub",
    "//evil.org/hub",
    "/hubevil",
    "/hub/../explore",
    "/explore?x=/hub",
    "/hub/login",
  ])("doesn't redirect outside the Hub after the login (%s)", async (next) => {
    const backend = sessionBackend()
    const login = await mountLogin(
      `/hub/login?next=${encodeURIComponent(next)}`,
    )
    await login.find("input").setValue(MEMBER.email)
    await login.find("form").trigger("submit")
    await flushPromises()
    const linkRequest = backend.requests.find(
      (r) => r.route == "hub/login-link",
    )!
    expect(linkRequest.body).toEqual({ email: MEMBER.email, next: "/hub" })
    login.unmount()
    wrapper = null

    const fromEmail = await mountLogin(
      `/hub/login?next=${encodeURIComponent(next)}#token=abc`,
    )
    findButton(fromEmail.element, "Log in")!.click()
    await afterNavigation(() =>
      expect(router.currentRoute.value.fullPath).toBe("/hub/T123456"),
    )
  })
})
