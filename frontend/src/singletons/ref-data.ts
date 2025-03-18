import { get } from "../services/api"
import {
  initDateWithPrecision,
  initDateProperty,
  type DateWithPrecision,
} from "@/utils/data-utils"

interface ApiData {
  [key: string]: any
}

interface Identifier extends ApiData {
  registry: string
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
  backer_name?: string
  hide_amount: boolean
  date_data_update?: Date
  date_data_start?: Date
  date_data_end?: Date
}

export interface Entity extends ApiData {
  id: string
  name: string
  country?: string
  identifiers: Identifier[]
  coordinates?: string
  logo?: string
  is_recipient: boolean
  is_partner: boolean
}

export interface EntityDetails extends Entity {
  date_inception?: Date
  description?: string
  website?: string
  wikipedia_url?: string
  wikipedia_extract?: string
  infrastructure?: InfrastructureDetails
  is_emitter: boolean
  is_agent: boolean
}

export interface Transfer extends ApiData {
  id: string
  emitter_id: string
  emitter?: DeepReadonly<Entity>
  recipient_id: string
  recipient?: DeepReadonly<Entity>
  agent_id: string | null
  agent?: DeepReadonly<Entity>
  amount: number | null
  currency: string | null
  amounts_clc?: Record<string, number>
  date_clc: DateWithPrecision
  description: string | null
  source: string
}

export interface TransferDetails extends Transfer {
  date_agreement: DateWithPrecision | null
  date_invoice: DateWithPrecision | null
  date_payment: DateWithPrecision | null
  date_start: DateWithPrecision | null
  date_end: DateWithPrecision | null
  raw_data: Record<string, any>
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
  transfers?: Transfer[]
  initialized: boolean
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
  currencies: {},
  initialized: false,
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
  const result = await get("entities/summary/?format=json", true)
  if (result.error || !result.data) {
    return null
  }
  const mapping: Record<string, Entity> = {}
  Array.from(result.data as Array<Entity>).forEach((e) => {
    mapping[e.id] = e
  })
  refData.entities = mapping
  return refData.entities
}

export function getEntitySummary(id: string): DeepReadonly<Entity> {
  return refData.entities[id]
}

export async function getEntityDetails(
  id: string,
): Promise<DeepReadonly<EntityDetails> | null> {
  const url = getEntityApiUrl(id)
  const result = await get(url, true)
  if (result.data) {
    const val = result.data as Record<string, any>
    initDateProperty(val, "date_inception")
    if (val.infrastructure) {
      for (const property of [
        "date_scoss_start",
        "date_scoss_end",
        "date_data_start",
        "date_data_end",
        "date_data_update",
      ]) {
        initDateProperty(val.infrastructure, property)
      }
    }
    return val as EntityDetails
  }
  return null
}

function processTransferEntities<T extends Transfer>(transfer: T) {
  transfer.emitter = refData.entities[transfer.emitter_id]
  transfer.recipient = refData.entities[transfer.recipient_id]
  transfer.agent = transfer.agent_id
    ? refData.entities[transfer.agent_id]
    : undefined
  initDateWithPrecision(transfer.date_clc)
}

/**
 * Get transfer list from the API and process the result data:
 *  - Process entities: fill emitter, recipient and agent with the refData's entities.
 *  - Process date_clc: create date object from raw string.
 * @param entity_id
 * @returns
 */
export async function getTransfers(
  entityId?: string,
): Promise<Transfer[] | null> {
  const queryParams = new URLSearchParams({})
  if (entityId) {
    queryParams.set("entity_id", entityId)
  }
  const result = await get("transfers/all/", true, queryParams)
  if (result.error || !result.data) {
    return null
  }
  const data = result.data as Transfer[]
  for (const transfer of data) {
    processTransferEntities(transfer)
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
    "date_payment",
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

export async function getEmittersForEntity(
  entityId: string,
): Promise<Entity[] | null> {
  const queryParams = new URLSearchParams({ entity_id: entityId })
  const result = await get("entities/emitters/", true, queryParams)
  if (result.error || !result.data) {
    return null
  }
  return result.data as Entity[]
}

export function getInfrastructures(): DeepReadonly<Entity>[] {
  return Object.values(refData.entities).filter((e) => e.is_recipient)
}

export function getEmitters(): DeepReadonly<Entity>[] {
  return Object.values(refData.entities).filter((e) => !e.is_recipient)
}

export function getPartners(): DeepReadonly<Entity>[] {
  return Object.values(refData.entities).filter((e) => e.is_partner)
}
