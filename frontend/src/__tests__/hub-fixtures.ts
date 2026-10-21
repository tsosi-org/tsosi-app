/**
 * Data of an organization's Hub for the tests, as the API sends it: an
 * organization, the infrastructures it supports, its transfers and its
 * declarations, with defaults to override.
 */
import type { Declaration, Submission } from "@/singletons/hub-declarations"
import type { Entity, EntityDetails, HubTransfer } from "@/singletons/ref-data"
import type { DateWithPrecision } from "@/utils/data-utils"

export function entity(values: Partial<Entity> & { id: string }): Entity {
  return {
    name: values.id,
    identifiers: [],
    is_partner: false,
    is_emitter: false,
    is_agent: false,
    is_recipient: false,
    is_scoss: false,
    is_posi: false,
    is_barcelona: false,
    is_public: true,
    is_new: false,
    ...values,
  } as Entity
}

// The organization whose Hub it is
export const ORG: EntityDetails = {
  ...entity({
    id: "org",
    name: "University of Testing",
    identifiers: [{ registry: "tsosi", value: "T123456" }],
    is_emitter: true,
  }),
  children: [],
}
export const DOAJ = entity({
  id: "doaj",
  name: "Directory of Open Access Journals",
  short_name: "DOAJ",
  is_recipient: true,
  scope: "in_scope",
})
export const ARXIV = entity({
  id: "arxiv",
  name: "arXiv",
  is_recipient: true,
  scope: "in_scope",
})
export const COUPERIN = entity({
  id: "couperin",
  name: "Couperin consortium",
  short_name: "Couperin",
  is_agent: true,
})
export const ENTITIES: Record<string, Entity> = Object.fromEntries(
  [ORG, DOAJ, ARXIV, COUPERIN].map((e) => [e.id, e]),
)

// A date as typed, `2024`, `2024-03` or `2024-03-13`, as the API sends it
export function apiDate(text: string): DateWithPrecision {
  const [year, month, day] = text.split("-")
  return {
    value: `${year}-${month ?? "01"}-${day ?? "01"}`,
    precision: day ? "day" : month ? "month" : "year",
  }
}

// A date as the frontend holds it once loaded
export function date(text: string): DateWithPrecision {
  const result = apiDate(text)
  return { ...result, dateObj: new Date(result.value) }
}

// A transfer of the organization's table: to DOAJ in 2024, declared by DOAJ
export function transfer(values: Partial<HubTransfer> = {}): HubTransfer {
  const received = values.date_payment_recipient ?? apiDate("2024")
  return {
    id: "t1",
    emitter_id: ORG.id,
    recipient_id: DOAJ.id,
    agent_ids: [],
    amount: 1000,
    currency: "EUR",
    amounts_clc: { EUR: 1000, USD: 1100 },
    date_clc: received,
    date_invoice: null,
    date_payment_emitter: null,
    date_payment_recipient: received,
    date_start: null,
    date_end: null,
    description: null,
    amount_hidden: false,
    declared_by: [
      { id: DOAJ.id, name: DOAJ.name, short_name: "DOAJ", date: "2025-01-01" },
    ],
    status: "not_confirmed",
    is_public: true,
    ...values,
  }
}

// A draft declaration of the organization
export function declaration(values: Partial<Declaration> = {}): Declaration {
  return {
    id: 1,
    kind: "confirmation",
    status: "draft",
    transfer_id: "t1",
    recipient_id: null,
    agent_ids: [],
    other_transfer_ids: [],
    other_declaration_ids: [],
    amount: null,
    currency: null,
    date_invoice: null,
    date_payment_emitter: null,
    date_payment_recipient: null,
    date_start: null,
    date_end: null,
    author: "member@uni.edu",
    date_last_updated: "2026-10-01T10:00:00Z",
    ...values,
  }
}

// A new support declared by the organization: to arXiv in 2025, 500 EUR
export function newSupport(values: Partial<Declaration> = {}): Declaration {
  return declaration({
    kind: "new",
    transfer_id: null,
    recipient_id: ARXIV.id,
    amount: 500,
    currency: "EUR",
    date_invoice: apiDate("2025"),
    ...values,
  })
}

export function submission(values: Partial<Submission> = {}): Submission {
  return {
    id: 1,
    status: "submitted",
    consent_at: "2026-10-01T10:00:00Z",
    submitted_by: "member@uni.edu",
    changes_count: 1,
    ...values,
  }
}
