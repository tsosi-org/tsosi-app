/**
 * Organizations of the Data Contribution Hub: the search over the TSOSI
 * organizations to pick the beneficiary and intermediaries of a support, and
 * the addition of those missing from TSOSI, from their ROR or Wikidata ID or
 * their name. Those are created in TSOSI at once, but aren't public until a
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

export const SCOPE_LABELS: Record<EntityScope, string> = {
  in_scope: "In scope",
  to_check: "To be checked",
  out_of_scope: "Not in scope",
}

export const SCOPE_SEVERITIES: Record<EntityScope, string> = {
  in_scope: "success",
  to_check: "warn",
  out_of_scope: "secondary",
}

export const SCOPE_INFOS: Record<EntityScope, string> = {
  in_scope: "In TSOSI's scope: its supports are published.",
  to_check:
    "To be checked by the TSOSI curation board: its supports are hidden on the public page until it's in TSOSI's scope.",
  out_of_scope:
    "Not in TSOSI's scope: its supports are hidden on the public page.",
}

/**
 * The scope of a beneficiary, or the one it will have once its support is
 * published: a beneficiary without scope, a new one included, is to be
 * checked by the curation board.
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
