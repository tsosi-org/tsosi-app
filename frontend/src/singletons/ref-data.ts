/**
 * This defines base types for the external TSOSI API along with
 * methods to interact with it.
 */
import { apiRequest, fetchUrl, get } from "@/services/api"
import {
  initDateProperty,
  initDateWithPrecision,
  shuffleArray,
  type DateWithPrecision,
} from "@/utils/data-utils"



type IdentifierRegistry = "ror" | "wikidata" | "_custom" | "tsosi"

interface ApiData {
  [key: string]: any
}

export interface ApiPaginatedData<T extends ApiData> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

interface Identifier extends ApiData {
  registry: IdentifierRegistry
  value: string
  registry_url?: string
}

export type TransferEntityType = "emitter" | "recipient" | "agent"

export interface Country extends ApiData {
  capital: string
  code: string
  continent: string
  flag_1x1: string
  flag_4x3: string
  iso: boolean
  name: string
  coordinates: [number, number] | null
}

export interface InfrastructureDetails extends ApiData {
  infra_finder_url?: string
  posi_url?: string
  support_url?: string
  date_scoss_start?: Date
  date_scoss_end?: Date
  legal_entity_wikidata_id?: string
}

// Whether a beneficiary is in TSOSI's scope: only the supports to those in
// scope are public
export type EntityScope = "in_scope" | "out_of_scope" | "to_check"

export interface Entity extends ApiData {
  id: string
  name: string
  short_name?: string
  country?: string
  identifiers: Identifier[]
  coordinates?: string
  logo?: string
  icon?: string
  is_partner: boolean
  is_emitter: boolean
  is_agent: boolean
  is_recipient: boolean
  is_scoss: boolean
  is_posi: boolean
  is_barcelona: boolean
  is_child_transfer?: boolean
  // Sent by the Hub only. The scope is null for the entities that aren't
  // beneficiaries. `is_new`: added in the Hub, without published support yet.
  scope?: EntityScope | null
  is_public?: boolean
  is_new?: boolean
}

export interface EntityDetails extends Entity {
  date_inception?: Date
  description?: string
  website?: string
  wikipedia_url?: string
  wikipedia_extract?: string
  // Institutions only
  open_science_policy_url?: string | null
  infrastructure?: InfrastructureDetails
  date_data_update?: Date
  children: string[]
}

export interface Transfer extends ApiData {
  id: string
  emitter_id: string
  emitter?: DeepReadonly<Entity>
  recipient_id: string
  recipient?: DeepReadonly<Entity>
  agent_ids: string[]
  agents?: DeepReadonly<Entity>[]
  amount: number | null
  currency: string | null
  amounts_clc?: Record<string, number>
  date_clc: DateWithPrecision
  description: string | null
  source_ids?: string[]
  sources?: DeepReadonly<Entity>[]
}

export type SupportStatus = "confirmed" | "not_confirmed"

// An organization that declared a transfer, with the date of its data
export interface Declarant {
  id: string | null
  name: string
  short_name: string | null
  date: string
}

// A transfer of an organization's supports table in the Hub
export interface HubTransfer extends Transfer {
  date_invoice: DateWithPrecision | null
  date_payment_emitter: DateWithPrecision | null
  date_payment_recipient: DateWithPrecision | null
  date_start: DateWithPrecision | null
  date_end: DateWithPrecision | null
  amount_hidden: boolean
  declared_by: Declarant[]
  status: SupportStatus
  // On the public site, with its page
  is_public: boolean
}

// A transfer of the preview of the organization's public page, once its
// changes are published: not converted into other currencies when new or
// changed
export interface PreviewTransfer extends HubTransfer {
  unconverted: boolean
}

export interface TransferDetails extends Transfer {
  emitter_sub: string | null
  date_invoice: DateWithPrecision | null
  date_payment_recipient: DateWithPrecision | null
  date_payment_emitter: DateWithPrecision | null
  date_start: DateWithPrecision | null
  date_end: DateWithPrecision | null
}

export interface Currency {
  id: string
  name: string
}

export interface Analytic extends ApiData {
  id: number
  recipient: string
  year: number
  country: string | null
  data: Record<string, any>
}

export type RefData = {
  countries: DeepReadonly<Record<string, Country>>
  entities: DeepReadonly<Record<string, Entity>>
  currencies: DeepReadonly<Record<string, Currency>>
  identifiers: Record<IdentifierRegistry, { [id: string]: string }>
  transfers?: Transfer[]
  initialized: boolean
  infrastructures: DeepReadonly<Entity>[]
}

export interface PaginatedResults<T> {
  count: number
  next?: string
  previous?: string
  results: Array<T>
}

export type DeepReadonly<T> = {
  readonly [K in keyof T]: T[K] extends (...args: any[]) => any
    ? T[K]
    : DeepReadonly<T[K]>
}

const refData: RefData = {
  countries: {},
  entities: {},
  identifiers: {
    tsosi: {},
    ror: {},
    wikidata: {},
    _custom: {},
  },
  currencies: {},
  initialized: false,
  infrastructures: [],
}

/**
 * Initialize the referential data used by the application.
 * This should be performed only once on startup.
 * @returns Whether the ref. data was correctly initialized.
 */
async function _initRefData(): Promise<boolean> {
  const promiseResults = await Promise.all([
    getEntities(),
    getCountries(),
    getCurrencies(),
  ])
  getInfrastructures()
  refData.initialized = true
  const correctlyLoaded = !promiseResults.some((res) => res == null)
  return correctlyLoaded
}

export const refDataPromise = _initRefData()

/**
 * Return the refData's countries.
 * Country data is taken from https://flagicons.lipis.dev/
 * @returns
 */
export async function getCountries(): Promise<DeepReadonly<
  Record<string, Country>
> | null> {
  if (refData.initialized) {
    return refData.countries
  }
  const result = await get("static_data/country.json", false, undefined, true)
  if (result.error || !result.data) {
    return null
  }
  const countries: Record<string, Country> = {}
  Array.from(result.data as Array<Country>).forEach((c) => {
    countries[c.code.toUpperCase()] = c
  })
  refData.countries = countries
  return refData.countries
}

export function getCountry(country_code: string): DeepReadonly<Country> {
  return refData.countries[country_code]
}

function getEntityApiUrl(id: string): string {
  return `entities/${id}`
}

export async function getEntities(): Promise<DeepReadonly<
  Record<string, Entity>
> | null> {
  if (refData.initialized) {
    return refData.entities
  }
  const result = await get("entities/all/", true)
  if (result.error || !result.data) {
    return null
  }
  const mapping: Record<string, Entity> = {}
  const identifierMapping: Record<
    IdentifierRegistry,
    { [id: string]: string }
  > = {
    ror: {},
    wikidata: {},
    _custom: {},
    tsosi: {},
  }
  Array.from(result.data as Array<Entity>).forEach((e) => {
    mapping[e.id] = e
    // Build the identifier -> entityId mapping
    for (const identifier of e.identifiers) {
      identifierMapping[identifier.registry][identifier.value] = e.id
    }
  })
  refData.entities = mapping
  refData.identifiers = identifierMapping
  return refData.entities
}

export function getEntitiesFromTransfers(transfers: Transfer[]): Record<string, Entity[]> {
  const entities: Record<string, Record<string, Entity>> = {
    emitters: {},
    recipients: {},
    agents: {},
  }
  for (const transfer of transfers) {
    if (!entities[transfer.emitter_id]) {
      entities["emitters"][transfer.emitter_id] = refData.entities[transfer.emitter_id] as Entity
    }
    if (!entities[transfer.recipient_id]) {
      entities["recipients"][transfer.recipient_id] = refData.entities[transfer.recipient_id] as Entity
    }
    for (const agentId of transfer.agent_ids) {
      if (!entities[agentId]) {
        entities["agents"][agentId] = refData.entities[agentId] as Entity
      }
    }
  }
  return {
    emitters: Object.values(entities["emitters"]),
    recipients: Object.values(entities["recipients"]),
    agents: Object.values(entities["agents"]),
  }
}

export function getEntitySummary(id: string): DeepReadonly<Entity> | null {
  return refData.entities[id]
}

const tsosiIdRegex = new RegExp("^T[0-9]{6,}$")
const rorIdRegex = new RegExp("^0[a-z|0-9]{6}[0-9]{2}$")
const wikidataIdRegex = new RegExp("^Q[0-9]+$")
const uuid4Regex = new RegExp(
  "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
)

/**
 * Return the entity corresponding to the given ID.
 * The ID must be one of the allowed registries.
 * @param id
 */
export function entityFromIdentifierId(id: string): string | undefined {
  if (tsosiIdRegex.test(id)) {
    return refData.identifiers.tsosi[id]
  } else if (rorIdRegex.test(id)) {
    return refData.identifiers.ror[id]
  } else if (wikidataIdRegex.test(id)) {
    return refData.identifiers.wikidata[id]
  }
  return refData.identifiers._custom[id]
}

export function resolveEntityRoute(id: string): string | undefined {
  if (uuid4Regex.test(id)) {
    return id
  }
  return entityFromIdentifierId(id)
}

function processEntityDetails(val: Record<string, any>): EntityDetails {
  initDateProperty(val, "date_inception")
  initDateProperty(val, "date_data_update")
  if (val.infrastructure) {
    for (const property of ["date_scoss_start", "date_scoss_end"]) {
      initDateProperty(val.infrastructure, property)
    }
  }
  return val as EntityDetails
}

export async function getEntityDetails(
  id: string,
): Promise<DeepReadonly<EntityDetails> | null> {
  const url = getEntityApiUrl(id)
  const result = await get(url, true)
  if (result.data) {
    return processEntityDetails(result.data as Record<string, any>)
  }
  return null
}

// Why an entity is not on the public site yet
export type PreviewReason = "to_check" | "out_of_scope" | "no_public_support"

/**
 * Get the details of an entity, public or not, for its members and the TSOSI
 * team (Hub session): the preview of a page not public yet.
 * Return null for anyone else.
 */
export async function getEntityPreview(id: string): Promise<{
  entity: EntityDetails
  reason: PreviewReason | null
} | null> {
  const result = await apiRequest(`hub/entities/${id}`)
  if (result.error || !result.data) {
    return null
  }
  const { preview_reason, ...data } = result.data
  return { entity: processEntityDetails(data), reason: preview_reason }
}

/**
 * The entities sent by the Hub, missing from the reference data or with
 * details it lacks (their scope), completed with the reference data.
 */
export function hubEntities(
  entities: Record<string, Partial<Entity>>,
): Record<string, Entity> {
  const result: Record<string, Entity> = {}
  for (const [id, entity] of Object.entries(entities)) {
    // Without identifiers, their links use the TSOSI ID
    result[id] = {
      ...(refData.entities[id] ?? { identifiers: [] }),
      ...entity,
    } as Entity
  }
  return result
}

/**
 * Fill the transfer's entities from the reference data, or from
 * `otherEntities` (see `hubEntities`).
 */
function processTransferEntities<T extends Transfer>(
  transfer: T,
  entity?: DeepReadonly<EntityDetails>,
  otherEntities: Record<string, Entity> = {},
): void {
  const getEntity = (id: string) => otherEntities[id] ?? refData.entities[id]
  transfer.emitter = getEntity(transfer.emitter_id)
  transfer.recipient = getEntity(transfer.recipient_id)
  transfer.agents = transfer.agent_ids.map(getEntity)
  if (transfer.source_ids) {
    transfer.sources = transfer.source_ids.map((id) => refData.entities[id])
  }
  initDateWithPrecision(transfer.date_clc)
  if (entity && entity.children && entity.children.some((c: string) => c == transfer.emitter_id)) {
    transfer.emitter = {
      ...transfer.emitter,
      is_child_transfer: true,
    } as Entity
  }
}

/**
 * Get transfer list from the API and process the result data:
 *  - Process entities: fill emitter, recipient and agents with the refData's entities.
 *  - Process date_clc: create date object from raw string.
 * @param entity_id
 * @returns
 */
export async function getTransfers(
  entity: EntityDetails
): Promise<Transfer[] | null> {
  const queryParams = new URLSearchParams({entity_id: entity.id})
  const result = await get("transfers/all/", true, queryParams)
  if (result.error || !result.data) {
    return null
  }
  const data = result.data as Transfer[]
  for (const transfer of data) {
    processTransferEntities(transfer, entity)
  }
  return data
}

export async function getTransferDetails(
  transferId: string,
): Promise<TransferDetails | null> {
  const url = `transfers/${transferId}`
  const result = await get(url, true)
  if (result.error) {
    return null
  }
  const transfer = result.data as TransferDetails
  processTransferEntities(transfer)
  for (const f of [
    "date_agreement",
    "date_payment_recipient",
    "date_payment_emitter",
    "date_invoice",
    "date_start",
    "date_end",
  ]) {
    initDateWithPrecision(transfer[f])
  }
  return transfer
}

export async function getCurrencies(): Promise<DeepReadonly<
  Record<string, Currency>
> | null> {
  if (refData.initialized) {
    return refData.currencies
  }
  const result = await get("currencies/", true)
  if (result.error || !result.data) {
    return null
  }
  const mapping: Record<string, Currency> = {}
  Array.from(result.data as Array<Currency>).forEach((c) => {
    mapping[c.id] = c
  })
  refData.currencies = mapping

  return refData.currencies
}

export async function getAnalytics(
  entityId: string,
): Promise<Analytic[] | null> {
  const queryParams = new URLSearchParams({ recipient_id: entityId })
  const result = await get("analytics/", true, queryParams)
  if (result.error || !result.data) {
    return null
  }
  return result.data as Analytic[]
}

/**
 * The infrastructures order is random, but we keep the order throughout the
 * navigation to avoid strange effects.
 * @returns
 */
export function getInfrastructures(): DeepReadonly<Entity>[] {
  if (!refData.initialized) {
    refData.infrastructures = Object.values(refData.entities).filter(
      (e) => e.is_recipient,
    )
    shuffleArray(refData.infrastructures)
  }
  return refData.infrastructures
}

export function getEmitters(): DeepReadonly<Entity>[] {
  return Object.values(refData.entities).filter((e) => !e.is_recipient)
}

export function getPartners(): DeepReadonly<Entity>[] {
  return Object.values(refData.entities).filter((e) => e.is_partner)
}

export async function entitySearch(
  query: string,
): Promise<ApiPaginatedData<Entity> | null> {
  if (!query) {
    return null
  }
  const queryParams = new URLSearchParams({
    search: query,
    ordering: "-is_recipient,name",
  })
  const result = await get("entities/", true, queryParams)
  if (result.error || !result.data) {
    return null
  }
  return result.data as ApiPaginatedData<Entity>
}

export async function queryPaginatedApiUrl<T extends ApiData>(
  query: string,
): Promise<ApiPaginatedData<T> | null> {
  if (!query) {
    return null
  }
  const result = await fetchUrl(query, true)
  if (result.error || !result.data) {
    return null
  }
  return result.data as ApiPaginatedData<T>
}


/**
 * Get the supports table of an organization, for its members and the TSOSI
 * team (Hub session): its transfers of all scopes, with their amounts.
 * The entities not on the public site come with the response.
 */
export async function getHubTransfers(
  entity: DeepReadonly<EntityDetails>,
): Promise<{
  transfers: HubTransfer[]
  entities: Record<string, Entity>
} | null> {
  const result = await apiRequest(`hub/entities/${entity.id}/transfers`)
  if (result.error || !result.data) {
    return null
  }
  const otherEntities = hubEntities(result.data.entities)
  const transfers = result.data.transfers as HubTransfer[]
  for (const transfer of transfers) {
    processTransferEntities(transfer, entity, otherEntities)
    for (const field of [
      "date_invoice",
      "date_payment_emitter",
      "date_payment_recipient",
      "date_start",
      "date_end",
    ] as const) {
      initDateWithPrecision(transfer[field])
    }
  }
  return { transfers, entities: otherEntities }
}

/**
 * Get the organization's public supports once its unpublished changes are
 * published, simulated by the Hub: the transfers, and the kinds of changes
 * of each, by transfer ID.
 */
export async function getPublicationPreview(
  entity: DeepReadonly<EntityDetails>,
): Promise<{
  transfers: PreviewTransfer[]
  changes: Record<string, string[]>
  // The drafts previewed, and a hash of their values, to submit (see
  // `submitDeclarations`)
  declarationIds: number[]
  declarationsHash: string
} | null> {
  const result = await apiRequest(
    `hub/entities/${entity.id}/publication-preview`,
  )
  if (result.error || !result.data) {
    return null
  }
  const otherEntities = hubEntities(result.data.entities)
  const transfers = result.data.transfers as PreviewTransfer[]
  for (const transfer of transfers) {
    processTransferEntities(transfer, entity, otherEntities)
  }
  return {
    transfers,
    changes: result.data.changes,
    declarationIds: result.data.declaration_ids,
    declarationsHash: result.data.declarations_hash,
  }
}
