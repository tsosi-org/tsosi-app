/**
 * Session of the Data Contribution Hub: the logged in member, or TSOSI team
 * member (Django admin session), and the login and logout requests.
 * The session is a cookie set by the backend, on the same origin as the
 * frontend. Write requests send the CSRF token of the `csrftoken` cookie.
 * The login token is sent by e-mail in a link like `/hub/login#token=<token>`.
 */
import { reactive, readonly } from "vue"
import type { RouteLocationNormalized } from "vue-router"

import { apiRequest, type ApiRequestResult } from "@/services/api"

const HASH_PREFIX = "#token="
// The path of a Hub page: `/hub`, then segments like an organization's ID
const HUB_PATH = /^\/hub(?:\/[\w-]+)*\/?$/
const MAX_NEXT_LENGTH = 2000

export interface Member {
  email: string
  is_staff: boolean
  // Empty for the TSOSI team members without a membership
  organization: {
    id: string
    // The ID of its Hub's URLs
    tsosi_id: string | null
    name: string
  } | null
  can_declare_supports: boolean
}

const state = reactive<{ member: Member | null; loaded: boolean }>({
  member: null,
  loaded: false,
})
// The login token extracted from the URL, waiting for the member to log in
let loginToken: string | null = null

export const session = readonly(state)

export function csrfHeaders(): Record<string, string> {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? { "X-CSRFToken": decodeURIComponent(match[1]) } : {}
}

function hubRequest(
  route: string,
  method: string = "GET",
  body?: object,
): Promise<ApiRequestResult> {
  const headers = method == "GET" ? {} : csrfHeaders()
  return apiRequest(`hub/${route}`, method, body, headers)
}

/**
 * Load the logged in member, once unless forced.
 * It also sets the CSRF cookie needed by the login requests.
 */
export async function loadSession(
  force: boolean = false,
): Promise<Member | null> {
  if (state.loaded && !force) {
    return state.member
  }
  const result = await hubRequest("me")
  state.member = result.error ? null : (result.data as Member)
  state.loaded = true
  return state.member
}

/**
 * The page to go to after the login, from the `next` param of the login
 * page: a Hub page of this site, with its query and hash, e.g. a shared
 * link to a filtered table. Null for anything else, so that the login can't
 * redirect elsewhere. The backend checks it the same way
 * (`tsosi/api/hub/session.py`).
 */
export function hubNextPath(next: unknown): string | null {
  if (typeof next != "string" || next.length > MAX_NEXT_LENGTH) {
    return null
  }
  const path = next.split(/[?#]/, 1)[0]
  // Not the login page itself
  return HUB_PATH.test(path) && !/^\/hub\/login\/?$/.test(path) ? next : null
}

/**
 * Ask for a login link sent by e-mail, leading to the `next` Hub page once
 * logged in.
 * Return the HTTP status: 204 when the request is accepted, whether or not
 * the e-mail belongs to a member.
 */
export async function requestLoginLink(
  email: string,
  next?: string,
): Promise<number | undefined> {
  await loadSession()
  const result = await hubRequest("login-link", "POST", {
    email,
    ...(next ? { next } : {}),
  })
  return result.status
}

/**
 * Log in with the token extracted from the login link.
 * Return whether the login succeeded.
 */
export async function logIn(): Promise<boolean> {
  if (!loginToken) {
    return false
  }
  await loadSession()
  const result = await hubRequest("login", "POST", { token: loginToken })
  loginToken = null
  if (result.error) {
    return false
  }
  state.member = result.data as Member
  return true
}

export async function logOut() {
  await hubRequest("logout", "POST")
  state.member = null
}

/**
 * Whether the logged in user can edit the entity's profile: a member of
 * that entity, or the TSOSI team.
 */
export function canEditEntity(entityId: string): boolean {
  const member = state.member
  return !!member && (member.is_staff || member.organization?.id == entityId)
}

export function hasLoginToken(): boolean {
  return loginToken !== null
}

/**
 * Router guard extracting the login token from the URL hash, if any.
 * It returns the same route without the hash, so that the token is neither
 * displayed nor tracked.
 */
export function extractLoginToken(to: RouteLocationNormalized) {
  if (to.name != "hub-login" || !to.hash.startsWith(HASH_PREFIX)) {
    return true
  }
  loginToken = decodeURIComponent(to.hash.slice(HASH_PREFIX.length)) || null
  return { path: to.path, query: to.query, hash: "", replace: true }
}

/**
 * Router guard of the Hub pages: members on their organization's
 * Hub, and the TSOSI team on any organization's Hub, read-only. Their URLs
 * have the organization's TSOSI ID (the Hub views redirect the TSOSI team's
 * other IDs).
 */
export async function hubGuard(to: RouteLocationNormalized) {
  if (!to.meta.hub) {
    return true
  }
  const member = await loadSession()
  if (!member) {
    return { name: "hub-login", query: { next: to.fullPath } }
  }
  if (member.is_staff && to.params.entityId) {
    return true
  }
  if (!member.organization) {
    // A TSOSI team member without a membership
    return { name: "home" }
  }
  const organization = member.organization
  const ref = organization.tsosi_id ?? organization.id
  if (to.params.entityId == organization.id && ref != organization.id) {
    // The same page, with the TSOSI ID
    return {
      name: to.name!,
      params: { ...to.params, entityId: ref },
      query: to.query,
      replace: true,
    }
  }
  if (!to.params.entityId) {
    // `/hub`: their organization's Hub, with the query of a shared link
    return { name: "hub-home", params: { entityId: ref }, query: to.query }
  }
  if (to.params.entityId != ref) {
    return { name: "hub-home", params: { entityId: ref } }
  }
  return true
}
