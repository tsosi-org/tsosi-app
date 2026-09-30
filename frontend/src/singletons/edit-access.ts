/**
 * Handles the temporary entity edit access keys.
 * The key is sent by e-mail in a link like `/entities/<id>#edit=<key>`.
 * It's stored in the session storage and removed from the URL.
 */
import { apiRequest } from "@/services/api"
import type { RouteLocationNormalized } from "vue-router"

const STORAGE_KEY = "tsosi-edit-key"
const HASH_PREFIX = "#edit="
// Fallback when the session storage is unavailable
let memoryKey: string | null = null

export interface EditAccess {
  email: string | null
  date_expires: string
}

export interface EntityEditData {
  name?: string
  short_name?: string | null
  country?: string | null
  date_inception?: string | null
  description?: string | null
  is_barcelona?: boolean
  website?: string | null
  wikipedia_url?: string | null
  identifiers?: {
    ror?: string | null
    wikidata?: string | null
  }
  infrastructure?: {
    support_url?: string | null
    posi_url?: string | null
    infra_finder_url?: string | null
    date_scoss_start?: string | null
    date_scoss_end?: string | null
  }
}

function getEditKey(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function setEditKey(key: string | null) {
  try {
    if (key) {
      sessionStorage.setItem(STORAGE_KEY, key)
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    // Storage unavailable: the edit access only lasts for the current page.
    memoryKey = key
  }
}

function currentKey(): string | null {
  return getEditKey() ?? memoryKey
}

/**
 * Router guard extracting the edit key from the URL hash, if any.
 * It returns the same route without the hash, so that the key is neither
 * displayed nor tracked.
 */
export function extractEditKey(to: RouteLocationNormalized) {
  if (!to.hash.startsWith(HASH_PREFIX)) {
    return true
  }
  const key = decodeURIComponent(to.hash.slice(HASH_PREFIX.length))
  setEditKey(key || null)
  return { path: to.path, query: to.query, hash: "", replace: true }
}

function authHeaders(): Record<string, string> {
  return { Authorization: `Bearer ${currentKey()}` }
}

/**
 * Check whether the stored edit key grants edit access to the entity.
 */
export async function checkEditAccess(
  entityId: string,
): Promise<EditAccess | null> {
  if (!currentKey()) {
    return null
  }
  const result = await apiRequest(
    `entities/${entityId}/edit/`,
    "GET",
    undefined,
    authHeaders(),
  )
  if (result.error) {
    return null
  }
  return result.data as EditAccess
}

/**
 * Submit the entity edits.
 * Return the updated entity details, or the validation errors.
 */
export async function submitEntityEdit(
  entityId: string,
  data: EntityEditData,
  logo?: File | null,
  icon?: File | null,
): Promise<{ ok: boolean; data: any; status?: number }> {
  let body: FormData | EntityEditData = data
  if (logo || icon) {
    body = new FormData()
    body.append("data", JSON.stringify(data))
    if (logo) {
      body.append("logo", logo)
    }
    if (icon) {
      body.append("icon", icon)
    }
  }
  const result = await apiRequest(
    `entities/${entityId}/edit/`,
    "PATCH",
    body,
    authHeaders(),
  )
  return { ok: !result.error, data: result.data, status: result.status }
}
