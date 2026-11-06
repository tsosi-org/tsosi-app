/**
 * Declarations of the Data Contribution Hub: the changes an organization
 * makes to its supports (new support, confirmation, edit, removal), and
 * whether possible duplicates are the same support (merge) or not, saved as
 * drafts until they're submitted and approved. Also the submissions.
 */
import { apiRequest, type ApiRequestResult } from "@/services/api"
import { csrfHeaders } from "@/singletons/hub-session"
import {
  hubEntities,
  type DeepReadonly,
  type Entity,
} from "@/singletons/ref-data"
import {
  initDateWithPrecision,
  type DatePrecision,
  type DateWithPrecision,
} from "@/utils/data-utils"

export type DeclarationKind =
  | "new"
  | "confirmation"
  | "edit"
  | "removal"
  | "merge"
  | "not_duplicate"
export type DeclarationStatus = "draft" | "submitted" | "approved"

export const KIND_LABELS: Record<DeclarationKind, string> = {
  new: "New support",
  confirmation: "Confirmation",
  edit: "Edit",
  removal: "Removal",
  merge: "Merge",
  not_duplicate: "Not a duplicate",
}

// The changes of one support: one pending per support
export const SUPPORT_CHANGE_KINDS: DeclarationKind[] = [
  "confirmation",
  "edit",
  "removal",
]
// About a transfer and `other_transfer_ids`: possible duplicates
export const RECONCILIATION_KINDS: DeclarationKind[] = [
  "merge",
  "not_duplicate",
]

// The five dates of the data collection schema, with their model field
export const DATE_FIELDS = [
  "date_invoice",
  "date_payment_emitter",
  "date_payment_recipient",
  "date_start",
  "date_end",
] as const
export type DateFieldName = (typeof DATE_FIELDS)[number]

export const DATE_LABELS: Record<DateFieldName, string> = {
  date_invoice: "Invoice date",
  date_payment_emitter: "Date sent",
  date_payment_recipient: "Date received",
  date_start: "Agreement start",
  date_end: "Agreement end",
}

// The editable cells of a row: the dates are typed in a panel under it,
// the others in the cell
export type EditorField =
  | "date"
  | "agents"
  | "recipient"
  | "amount"
  | "currency"

// The validation errors of each field
export const EDITOR_FIELD_ERRORS: Record<EditorField, string[]> = {
  date: [...DATE_FIELDS, "dates"],
  agents: ["agent_ids"],
  recipient: ["recipient_id"],
  amount: ["amount"],
  currency: ["currency"],
}

export interface Declaration {
  id: number
  kind: DeclarationKind
  status: DeclarationStatus
  transfer_id: string | null
  recipient_id: string | null
  agent_ids: string[]
  // A merge's transfers that are the same support as `transfer_id`, a
  // not-duplicate's that aren't, and the matches that a new support isn't
  other_transfer_ids: string[]
  // For a new support: the other new supports it isn't
  other_declaration_ids: number[]
  amount: number | null
  currency: string | null
  date_invoice: DateWithPrecision | null
  date_payment_emitter: DateWithPrecision | null
  date_payment_recipient: DateWithPrecision | null
  date_start: DateWithPrecision | null
  date_end: DateWithPrecision | null
  author: string | null
  date_last_updated: string
}

// What is sent on save. Dates are typed as `2024`, `2024-03` or `2024-03-13`.
export interface DeclarationPayload {
  kind: DeclarationKind
  transfer_id: string | null
  recipient_id?: string | null
  agent_ids?: string[]
  other_transfer_ids?: string[]
  other_declaration_ids?: number[]
  amount?: number | null
  currency?: string | null
  date_invoice?: string | null
  date_payment_emitter?: string | null
  date_payment_recipient?: string | null
  date_start?: string | null
  date_end?: string | null
}

// Validation errors, by field
export type DeclarationErrors = Record<string, string[]>

// The values of a support being edited in the supports table, dates as typed
export interface SupportDraft {
  recipient: DeepReadonly<Entity> | null
  // One intermediary at most is entered for now
  agents: DeepReadonly<Entity>[]
  amount: number | null
  // The amount as typed, `amount` when it's valid
  amountText: string
  currency: string | null
  dates: Record<DateFieldName, string>
}

function declarationsRoute(entityId: string, id?: number): string {
  const base = `hub/entities/${entityId}/declarations`
  return id == null ? base : `${base}/${id}`
}

// The row of the supports table of a new support not published yet. The
// published supports' rows are their transfer IDs.
export function newRowId(declarationId: number): string {
  return `new-${declarationId}`
}

/**
 * Get the organization's declarations not published yet, their entities
 * missing from the reference data (see `hubEntities`), and the pairs of
 * rows of its supports table that may be the same support (row IDs, see
 * `newRowId`), not reconciled yet.
 */
export async function getDeclarations(entityId: string): Promise<{
  declarations: Declaration[]
  entities: Record<string, Entity>
  duplicates: [string, string][]
} | null> {
  const result = await apiRequest(declarationsRoute(entityId))
  if (result.error || !result.data) {
    return null
  }
  const entities = hubEntities(result.data.entities)
  const declarations = result.data.declarations as Declaration[]
  for (const declaration of declarations) {
    DATE_FIELDS.forEach((f) => initDateWithPrecision(declaration[f]))
  }
  return {
    declarations,
    entities,
    duplicates: result.data.possible_duplicates,
  }
}

/**
 * Save a declaration: a new one, or a draft when `id` is given.
 * The result's `data` holds the validation errors on a 400.
 */
export function saveDeclaration(
  entityId: string,
  payload: DeclarationPayload,
  id?: number,
): Promise<ApiRequestResult> {
  return apiRequest(
    declarationsRoute(entityId, id),
    id == null ? "POST" : "PUT",
    payload,
    csrfHeaders(),
  )
}

/**
 * Delete a draft declaration: undo the change.
 * The result's `data` holds the error, e.g. a 403 once it's submitted.
 */
export function deleteDeclaration(
  entityId: string,
  id: number,
): Promise<ApiRequestResult> {
  return apiRequest(
    declarationsRoute(entityId, id),
    "DELETE",
    undefined,
    csrfHeaders(),
  )
}

const DATE_INPUT_REGEX = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/

/**
 * Parse a typed date: `2024`, `2024-03` or `2024-03-13`, the precision
 * coming from what is typed. Return null if it isn't a valid date.
 */
export function parseDateInput(text: string): DateWithPrecision | null {
  const match = DATE_INPUT_REGEX.exec(text.trim())
  if (!match) {
    return null
  }
  const [, year, month, day] = match
  const value = `${year}-${month ?? "01"}-${day ?? "01"}`
  const dateObj = new Date(`${value}T00:00:00Z`)
  if (isNaN(dateObj.getTime()) || dateObj.toISOString().slice(0, 10) != value) {
    return null
  }
  const precision: DatePrecision = day ? "day" : month ? "month" : "year"
  return { value, precision, dateObj }
}

// A date as it's typed: `2024`, `2024-03` or `2024-03-13`
export function formatDateInput(date: DateWithPrecision | null): string {
  if (!date) {
    return ""
  }
  const length = { year: 4, month: 7, day: 10 }[date.precision]
  return date.value.slice(0, length)
}

/**
 * Parse a typed amount: digits, with a `.` or a `,` for the decimals
 * (`1500.50`, `1500,50`), spaces allowed to group the thousands
 * (`1 500,50`). A trailing separator is allowed while typing (`1500.` is
 * 1500). Any number of decimals, as the backend accepts, which checks that
 * it's positive. `{ amount: null }` when empty, null if it isn't an amount.
 */
export function parseAmountInput(
  text: string,
): { amount: number | null } | null {
  const value = text.replace(/\s/g, "")
  if (!value) {
    return { amount: null }
  }
  const parts = /^(\d*)(?:[.,](\d*))?$/.exec(value)
  if (!parts || !(parts[1] || parts[2])) {
    return null
  }
  const amount = Number(`${parts[1] || 0}.${parts[2] || 0}`)
  return Number.isFinite(amount) ? { amount } : null
}

// An amount as it's typed again, with a `.` for the decimals
export function formatAmountInput(amount: number | null): string {
  return amount == null ? "" : String(amount)
}

/**
 * The date shown on the public page, with the rule of the backend's
 * `update_transfer_date_clc`: received, else sent, else invoice, else the
 * agreement start year.
 */
export function computeDateClc(
  dates: Partial<Record<DateFieldName, DateWithPrecision | null>>,
): { date: DateWithPrecision; field: DateFieldName } | null {
  for (const field of [
    "date_payment_recipient",
    "date_payment_emitter",
    "date_invoice",
  ] as const) {
    const date = dates[field]
    if (date) {
      return { date: { ...date }, field }
    }
  }
  const start = dates.date_start
  if (start) {
    return {
      date: { value: start.value, precision: "year", dateObj: start.dateObj },
      field: "date_start",
    }
  }
  return null
}

export type SubmissionStatus = "submitted" | "publishing"

// A submission waiting for approval by the TSOSI team
export interface Submission {
  id: number
  status: SubmissionStatus
  consent_at: string
  submitted_by: string | null
  changes_count: number
}

function submissionsRoute(entityId: string): string {
  return `hub/entities/${entityId}/submissions`
}

export async function getSubmissions(
  entityId: string,
): Promise<Submission[] | null> {
  const result = await apiRequest(submissionsRoute(entityId))
  if (result.error || !result.data) {
    return null
  }
  return result.data as Submission[]
}

/**
 * Submit all the organization's draft declarations for approval, with the
 * agreement to their publication under CC BY-SA 4.0. They must be those
 * previewed, with the values previewed (`declarationIds` and
 * `declarationsHash` of the preview): a 400 if they changed since, e.g. by
 * another member.
 */
export function submitDeclarations(
  entityId: string,
  preview: { declarationIds: readonly number[]; declarationsHash: string },
): Promise<ApiRequestResult> {
  return apiRequest(
    submissionsRoute(entityId),
    "POST",
    {
      consent: true,
      declaration_ids: preview.declarationIds,
      declarations_hash: preview.declarationsHash,
    },
    csrfHeaders(),
  )
}
