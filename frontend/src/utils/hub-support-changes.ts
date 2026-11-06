/**
 * The changes that the supports table of the Data Contribution Hub
 * (`HubSupports`) saves: the declarations to save and delete when a row is
 * saved, confirmed, removed, undone, or reconciled with another one.
 */
import {
  DATE_FIELDS,
  DATE_LABELS,
  deleteDeclaration,
  EDITOR_FIELD_ERRORS,
  formatDateInput,
  parseAmountInput,
  saveDeclaration,
  type Declaration,
  type DeclarationErrors,
  type DateFieldName,
  type DeclarationPayload,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import type { HubTransfer } from "@/singletons/ref-data"
import {
  dismissedRows,
  isNewRow,
  valuesFromDeclaration,
  valuesFromDraft,
  valuesFromTransfer,
  type SupportRow,
  type SupportTable,
  type SupportValues,
} from "@/utils/hub-support-rows"

// The values sent on save, compared to tell an edit from a confirmation
export function payloadValues(values: SupportValues) {
  return {
    recipient_id: values.recipient?.id ?? null,
    agent_ids: values.agents.map((a) => a.id).sort(),
    amount: values.amount,
    currency: values.currency,
    ...Object.fromEntries(
      DATE_FIELDS.map((f) => [f, formatDateInput(values.dates[f]) || null]),
    ),
  }
}

export type PayloadValues = ReturnType<typeof payloadValues>

// The draft's values as typed: invalid dates are sent to get their errors
export function draftPayloadValues(draft: SupportDraft): PayloadValues {
  return {
    ...payloadValues(valuesFromDraft(draft)),
    ...Object.fromEntries(
      DATE_FIELDS.map((f) => [f, draft.dates[f].trim() || null]),
    ),
  }
}

export const AMOUNT_FORMAT_ERROR =
  "Enter an amount like 1500, 1500.50 or 1 500,50."

/**
 * The errors of the values typed, found before saving: the amount, required
 * in the Hub, and its format. The others are checked by the server.
 */
export function draftErrors(draft: SupportDraft): DeclarationErrors {
  const parsed = parseAmountInput(draft.amountText)
  if (!parsed) {
    return { amount: [AMOUNT_FORMAT_ERROR] }
  }
  if (parsed.amount == null) {
    return { amount: ["Enter the amount."] }
  }
  return {}
}

/**
 * The change of a published support declaring these values: none if the
 * organization already declared them, else a confirmation or an edit.
 */
export function supportChange(
  transfer: HubTransfer,
  values: PayloadValues,
): DeclarationPayload | null {
  const unchanged =
    JSON.stringify(values) ==
    JSON.stringify(payloadValues(valuesFromTransfer(transfer)))
  if (unchanged && transfer.status == "confirmed") {
    return null
  }
  return unchanged
    ? { kind: "confirmation", transfer_id: transfer.id }
    : { kind: "edit", transfer_id: transfer.id, ...values }
}

// A new support's declaration, with its values and the rows it isn't, of
// those still in the table
export function newSupportPayload(
  table: SupportTable,
  values: PayloadValues,
  otherRows: string[],
): DeclarationPayload {
  return {
    kind: "new",
    transfer_id: null,
    ...values,
    other_transfer_ids: otherRows.filter((id) => table.transferById.has(id)),
    other_declaration_ids: otherRows
      .filter((id) => id.startsWith("new-"))
      .map((id) => table.rowById.get(id)?.declaration?.id)
      .filter((id): id is number => id != null),
  }
}

// The declarations to save (new ones, or drafts with their ID), then those
// to delete
export interface Operations {
  saves: { payload: DeclarationPayload; id?: number }[]
  deletions: Declaration[]
}

/**
 * Turn a new support (a draft, or the values of the row being added) into
 * the change of the published support it is, replacing that support's
 * pending change, if any.
 */
export function asChangeOf(
  table: SupportTable,
  draft: Declaration | null,
  transferId: string,
  values: PayloadValues,
): Operations {
  const transfer = table.transferById.get(transferId)!
  const payload = supportChange(transfer, values)
  const existing = table.changeByTransfer.get(transferId)
  const result: Operations = { saves: [], deletions: [] }
  if (!payload) {
    result.deletions.push(
      ...[existing, draft].filter((d): d is Declaration => !!d),
    )
  } else if (existing) {
    result.saves.push({ payload, id: existing.id })
    if (draft) {
      result.deletions.push(draft)
    }
  } else {
    // A draft new support becomes the change of its match
    result.saves.push({ payload, id: draft?.id })
  }
  return result
}

/**
 * Save the values typed for a published support: its confirmation or edit,
 * or nothing if the organization already declared them.
 */
export function supportOperations(
  transfer: HubTransfer,
  draft: Declaration | null,
  values: PayloadValues,
): Operations {
  const payload = supportChange(transfer, values)
  if (!payload) {
    return { saves: [], deletions: draft ? [draft] : [] }
  }
  return { saves: [{ payload, id: draft?.id }], deletions: [] }
}

/**
 * Save the values typed for a new support (a draft, or the one being
 * added). A draft keeps the supports it was declared not to be. The saved
 * supports it may be show as its possible duplicates once saved.
 */
export function newSupportOperations(
  table: SupportTable,
  draft: Declaration | null,
  values: PayloadValues,
): Operations {
  const payload = newSupportPayload(table, values, dismissedRows(draft))
  return { saves: [{ payload, id: draft?.id }], deletions: [] }
}

/**
 * Tell whether two rows are the same support, or not. Two published
 * supports: a merge, or a not-duplicate. A new support and a published one:
 * the new one becomes the change of the published one, or lists it as a
 * support it isn't. Two new supports: one of them is removed, or one lists
 * the other. The new support changed is a draft, the right one if both are.
 */
export function reconcileOperations(
  table: SupportTable,
  left: SupportRow,
  right: SupportRow,
  same: boolean,
): Operations {
  const news = [left, right].filter(isNewRow)
  if (news.length == 0) {
    const payload: DeclarationPayload = {
      kind: same ? "merge" : "not_duplicate",
      transfer_id: left.id,
      other_transfer_ids: [right.id],
    }
    return { saves: [{ payload }], deletions: [] }
  }
  const draftRow = [right, left].find(
    (r) => isNewRow(r) && r.declaration!.status == "draft",
  )!
  const otherRow = draftRow == left ? right : left
  const declaration = draftRow.declaration!
  const values = payloadValues(
    valuesFromDeclaration(declaration, table.getEntity),
  )
  if (news.length == 2 && same) {
    return { saves: [], deletions: [declaration] }
  }
  if (same) {
    return asChangeOf(table, declaration, otherRow.id, values)
  }
  const payload = newSupportPayload(table, values, [
    ...dismissedRows(declaration),
    otherRow.id,
  ])
  return { saves: [{ payload, id: declaration.id }], deletions: [] }
}

/**
 * Save the changes, then delete the declarations, stopping at the first
 * error: its result.
 */
export async function runOperations(
  organizationId: string,
  { saves, deletions }: Operations,
): Promise<{ status?: number; data?: any } | null> {
  for (const { payload, id } of saves) {
    const result = await saveDeclaration(organizationId, payload, id)
    if (result.error) {
      return result
    }
  }
  for (const declaration of deletions) {
    const result = await deleteDeclaration(organizationId, declaration.id)
    if (result.error) {
      return result
    }
  }
  return null
}

const SAVE_ERROR = "The change couldn't be saved. Please try again."

// The errors of a response, by field, as lists of messages
function normalizeErrors(data: any): DeclarationErrors {
  const errors: DeclarationErrors = {}
  for (const [field, messages] of Object.entries(data ?? {})) {
    errors[field] = Array.isArray(messages)
      ? messages.map(String)
      : [String(messages)]
  }
  return errors
}

// The errors of a failed save of the row being edited, by field
export function saveErrors(result: {
  status?: number
  data?: any
}): DeclarationErrors {
  return result.status == 400 || result.status == 403
    ? normalizeErrors(result.data)
    : { detail: [SAVE_ERROR] }
}

// The errors of a failed action, as one message
export function errorMessage(data: any): string {
  return Object.values(normalizeErrors(data)).flat().join(" ") || SAVE_ERROR
}

/**
 * The messages of the errors of the row being edited, listed under it: those
 * of its cells in their order, then the others. A date's names it.
 */
export function errorMessages(errors: DeclarationErrors): string[] {
  const fieldKeys = Object.values(EDITOR_FIELD_ERRORS).flat()
  const keys = [
    ...fieldKeys,
    ...Object.keys(errors).filter((key) => !fieldKeys.includes(key)),
  ]
  return keys.flatMap((key) =>
    (errors[key] ?? []).map((message) =>
      key in DATE_LABELS
        ? `${DATE_LABELS[key as DateFieldName]}: ${message}`
        : message,
    ),
  )
}
