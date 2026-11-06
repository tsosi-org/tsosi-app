/**
 * Organizations of the Data Contribution Hub: the search over the TSOSI
 * organizations to pick the beneficiary and intermediaries of a support, and
 * the addition of those missing from TSOSI, from their ROR or Wikidata ID or
 * their name (`NewOrganizationPanel`). Those are created in TSOSI at once, but aren't public until a
 * support to them is published.
 */
import { apiRequest, type ApiRequestResult } from "@/services/api"
import { csrfHeaders } from "@/singletons/hub-session"
import type { DeepReadonly, Entity, EntityScope } from "@/singletons/ref-data"

// The record of a ROR or Wikidata ID missing from TSOSI
export interface RegistryRecord {
  registry: "ror" | "wikidata"
  identifier: string
  name: string | null
  country: string | null
  website: string | null
}

// The search of a ROR or Wikidata ID missing from TSOSI: its record, or the
// error
export interface RegistryLookup {
  registry: "ror" | "wikidata"
  identifier: string
  record: RegistryRecord | null
  error: string | null
}

// The URLs that members are likely to paste instead of the ID, and the IDs,
// as parsed by the backend (`parse_organization_id`)
const ROR_URL = /^(?:https?:\/\/)?(?:www\.)?ror\.org\//i
const ROR_ID = /^0[a-z0-9]{6}[0-9]{2}$/
const WIKIDATA_URL =
  /^(?:https?:\/\/)?(?:www\.|m\.)?wikidata\.org\/(?:wiki|entity)\//i
const WIKIDATA_ID = /^Q[0-9]+$/

/**
 * The registry and the ID of a ROR or Wikidata ID, or of its URL, or null if
 * it's neither, e.g. a name.
 */
export function parseOrganizationId(
  text: string,
): { registry: "ror" | "wikidata"; value: string } | null {
  const value = text.trim().replace(/\/+$/, "")
  const ror = value.replace(ROR_URL, "").toLowerCase()
  if (ROR_ID.test(ror)) {
    return { registry: "ror", value: ror }
  }
  const wikidata = value.replace(WIKIDATA_URL, "").toUpperCase()
  if (WIKIDATA_ID.test(wikidata)) {
    return { registry: "wikidata", value: wikidata }
  }
  return null
}

export const SCOPE_INFOS: Record<EntityScope, string> = {
  in_scope: "In TSOSI's scope: its supports are published.",
  to_check:
    "To be checked by the TSOSI team: its supports are hidden on the public page until it's in TSOSI's scope.",
  out_of_scope:
    "Not in TSOSI's scope: its supports are hidden on the public page.",
}

/**
 * The highlight of a beneficiary whose supports aren't public: an outline
 * and background color (`.scope-highlight` in `base.css`), explained by its
 * tooltip. None for a beneficiary in scope.
 */
export function scopeHighlight(
  scope: EntityScope,
): { class: string; tooltip: string } | null {
  if (scope == "in_scope") {
    return null
  }
  return {
    class: `scope-highlight scope-${scope.replace(/_/g, "-")}`,
    tooltip: SCOPE_INFOS[scope],
  }
}

/**
 * The scope of a beneficiary, or the one it will have once its support is
 * published: a beneficiary without scope, a new one included, is to be
 * checked by the TSOSI team.
 */
export function recipientScope(entity: DeepReadonly<Entity>): EntityScope {
  if (entity.scope !== undefined) {
    return entity.scope ?? "to_check"
  }
  // The reference data, without scopes, only has public beneficiaries, so in
  // scope (see the backend's `hub_entities`)
  return entity.is_recipient ? "in_scope" : "to_check"
}

function hubEntity(entity: Partial<Entity>): Entity {
  return { identifiers: [], ...entity } as Entity
}

/**
 * Search the TSOSI organizations, public or not, with their scope. The best
 * matches first. When the query is a ROR or Wikidata ID missing from TSOSI,
 * `lookup` holds its record.
 */
export async function searchOrganizations(query: string): Promise<{
  results: Entity[]
  lookup: RegistryLookup | null
} | null> {
  const params = new URLSearchParams({ search: query })
  const result = await apiRequest(`hub/organizations?${params}`)
  if (result.error || !result.data) {
    return null
  }
  return {
    results: (result.data.results as Partial<Entity>[]).map(hubEntity),
    lookup: result.data.lookup,
  }
}

/**
 * Add an organization missing from TSOSI, from its ROR or Wikidata ID, or
 * from its name. The result's `data` holds the entity, or the validation
 * errors on a 400.
 */
export async function addOrganization(
  entityId: string,
  values: { name: string } | { identifier: string },
): Promise<ApiRequestResult> {
  const result = await apiRequest(
    `hub/entities/${entityId}/organizations`,
    "POST",
    values,
    csrfHeaders(),
  )
  if (!result.error) {
    result.data = hubEntity(result.data)
  }
  return result
}
