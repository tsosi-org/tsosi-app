import { beforeEach, describe, expect, it, vi } from "vitest"
import type { RouteLocationNormalized } from "vue-router"

import { mockApi } from "@/__tests__/api-mock"
import type { Member } from "@/singletons/hub-session"

// The session state is module-level: a fresh module for each test
async function hubSession() {
  vi.resetModules()
  return await import("@/singletons/hub-session")
}

function route(
  values: Partial<RouteLocationNormalized> & { hub?: boolean },
): RouteLocationNormalized {
  const { hub = true, ...rest } = values
  return {
    name: "hub-home",
    path: "/hub",
    fullPath: "/hub",
    hash: "",
    query: {},
    params: {},
    matched: [],
    redirectedFrom: undefined,
    meta: { hub },
    ...rest,
  } as RouteLocationNormalized
}

const ORGANIZATION = { id: "uuid-1", tsosi_id: "T123456", name: "Uni" }

function member(values: Partial<Member> = {}): Member {
  return {
    email: "member@uni.edu",
    is_staff: false,
    organization: ORGANIZATION,
    can_declare_supports: true,
    ...values,
  }
}

function loggedInAs(value: Member | null) {
  return mockApi({
    "hub/me": value ? { body: value } : { status: 403 },
  })
}

describe("hubGuard", () => {
  beforeEach(() => {
    document.cookie = "csrftoken=; max-age=0"
  })

  it("lets the other pages through without loading the session", async () => {
    const requests = loggedInAs(null)
    const { hubGuard } = await hubSession()
    expect(await hubGuard(route({ hub: false }))).toBe(true)
    expect(requests).toEqual([])
  })

  it("sends the logged out users to the login, then back", async () => {
    loggedInAs(null)
    const { hubGuard } = await hubSession()
    const to = route({
      params: { entityId: "T123456" },
      fullPath: "/hub/T123456/submit?x=1",
    })
    expect(await hubGuard(to)).toEqual({
      name: "hub-login",
      query: { next: "/hub/T123456/submit?x=1" },
    })
  })

  it("lets a member in their organization's Hub", async () => {
    loggedInAs(member())
    const { hubGuard } = await hubSession()
    expect(await hubGuard(route({ params: { entityId: "T123456" } }))).toBe(
      true,
    )
  })

  it("redirects the organization's UUID to its TSOSI ID", async () => {
    loggedInAs(member())
    const { hubGuard } = await hubSession()
    const to = route({
      name: "hub-submit",
      params: { entityId: "uuid-1" },
      query: { tab: "x" },
    })
    expect(await hubGuard(to)).toEqual({
      name: "hub-submit",
      params: { entityId: "T123456" },
      query: { tab: "x" },
      replace: true,
    })
  })

  it("keeps the UUID of an organization without TSOSI ID", async () => {
    loggedInAs(member({ organization: { ...ORGANIZATION, tsosi_id: null } }))
    const { hubGuard } = await hubSession()
    expect(await hubGuard(route({ params: { entityId: "uuid-1" } }))).toBe(true)
  })

  it("sends a member elsewhere to their own Hub", async () => {
    loggedInAs(member())
    const { hubGuard } = await hubSession()
    const to = route({ params: { entityId: "T999999" }, query: { tab: "x" } })
    expect(await hubGuard(to)).toEqual({
      name: "hub-home",
      params: { entityId: "T123456" },
    })
  })

  it("sends a member from /hub to their own Hub, with the query", async () => {
    loggedInAs(member())
    const { hubGuard } = await hubSession()
    expect(await hubGuard(route({ query: { tab: "page" } }))).toEqual({
      name: "hub-home",
      params: { entityId: "T123456" },
      query: { tab: "page" },
    })
  })

  it("lets the TSOSI team in any organization's Hub", async () => {
    loggedInAs(member({ is_staff: true, organization: null }))
    const { hubGuard } = await hubSession()
    expect(await hubGuard(route({ params: { entityId: "T999999" } }))).toBe(
      true,
    )
    // Without an organization of their own, /hub leads nowhere
    expect(await hubGuard(route({}))).toEqual({ name: "home" })
  })

  it("loads the session once", async () => {
    const requests = loggedInAs(member())
    const { hubGuard } = await hubSession()
    await hubGuard(route({ params: { entityId: "T123456" } }))
    await hubGuard(route({ params: { entityId: "T123456" } }))
    expect(requests).toHaveLength(1)
  })
})

describe("login", () => {
  it("extracts the token from the URL hash and hides it", async () => {
    const { extractLoginToken, hasLoginToken } = await hubSession()
    const to = route({
      name: "hub-login",
      path: "/hub/login",
      hash: "#token=abc%2Bdef",
      query: { next: "/hub/T1" },
    })
    expect(extractLoginToken(to)).toEqual({
      path: "/hub/login",
      query: { next: "/hub/T1" },
      hash: "",
      replace: true,
    })
    expect(hasLoginToken()).toBe(true)
  })

  it.each([
    route({ name: "hub-login", hash: "#other" }),
    route({ name: "home", hash: "#token=abc" }),
  ])("ignores other hashes and pages", async (to) => {
    const { extractLoginToken, hasLoginToken } = await hubSession()
    expect(extractLoginToken(to)).toBe(true)
    expect(hasLoginToken()).toBe(false)
  })

  it("logs in once with the token, with the CSRF cookie", async () => {
    document.cookie = "csrftoken=xyz"
    const requests = mockApi({
      "hub/me": { status: 403 },
      "hub/login": { body: member() },
    })
    const { extractLoginToken, logIn, session } = await hubSession()
    extractLoginToken(route({ name: "hub-login", hash: "#token=abc" }))
    expect(await logIn()).toBe(true)
    expect(session.member?.email).toBe("member@uni.edu")
    const login = requests.find((r) => r.route == "hub/login")!
    expect(login.body).toEqual({ token: "abc" })
    expect(login.headers.get("X-CSRFToken")).toBe("xyz")
    // The token is used once
    expect(await logIn()).toBe(false)
  })

  it("fails with an invalid token", async () => {
    mockApi({ "hub/me": { status: 403 }, "hub/login": { status: 400 } })
    const { extractLoginToken, logIn, session } = await hubSession()
    extractLoginToken(route({ name: "hub-login", hash: "#token=abc" }))
    expect(await logIn()).toBe(false)
    expect(session.member).toBeNull()
  })
})

describe("hubNextPath", () => {
  it.each([
    "/hub",
    "/hub/",
    "/hub?tab=page&status=pending",
    "/hub/T123456?tab=page&f_name=a%20b#x",
    "/hub/T123456/submit",
  ])("accepts a Hub page with its query (%s)", async (next) => {
    const { hubNextPath } = await hubSession()
    expect(hubNextPath(next)).toBe(next)
  })

  it.each([
    undefined,
    ["/hub"],
    "",
    "hub",
    "https://evil.org/hub",
    "//evil.org/hub",
    "/\\evil.org/hub",
    "/hubevil",
    "/hub/../explore",
    "/hub/./x",
    "/hub/login",
    "/hub/login?next=/hub",
    "/explore?x=/hub",
    `/hub/${"x".repeat(2000)}`,
  ])("rejects anything else (%j)", async (next) => {
    const { hubNextPath } = await hubSession()
    expect(hubNextPath(next)).toBeNull()
  })
})

describe("canEditEntity", () => {
  it("is true for the organization's members and the TSOSI team", async () => {
    loggedInAs(member())
    const { canEditEntity, loadSession } = await hubSession()
    expect(canEditEntity("uuid-1")).toBe(false)
    await loadSession()
    expect(canEditEntity("uuid-1")).toBe(true)
    expect(canEditEntity("uuid-2")).toBe(false)

    loggedInAs(member({ is_staff: true, organization: null }))
    await loadSession(true)
    expect(canEditEntity("uuid-2")).toBe(true)
  })
})
