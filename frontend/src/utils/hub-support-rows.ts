/**
 * The rows of an organization's supports table in the Data Contribution Hub
 * (`HubSupports`): its transfers merged with its changes not published yet
 * (declarations), with their status, their possible duplicates, and the
 * other saved supports shown under a row (sub-rows).
 */
import {
  computeDateClc,
  DATE_FIELDS,
  formatAmountInput,
  formatDateInput,
  KIND_LABELS,
  newRowId,
  parseDateInput,
  RECONCILIATION_KINDS,
  SUPPORT_CHANGE_KINDS,
  type DateFieldName,
  type Declaration,
  type Match,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import type { DeepReadonly, Entity, HubTransfer } from "@/singletons/ref-data"
import type { DateWithPrecision } from "@/utils/data-utils"
import { supportLabel } from "@/utils/hub-supports"

// The status of a row, shown by its style
export type RowGroup =
  | "not_confirmed"
  | "confirmed"
  | "duplicate"
  | "unpublished"
  | "submitted"

// The statuses that need attention, colored and explained by the legend,
// whose items filter the table. Confirmed rows have neither.
export type FilterGroup = Exclude<RowGroup, "confirmed">

function filterGroup(row: { group: RowGroup }): FilterGroup | null {
  return row.group == "confirmed" ? null : row.group
}

// The values of a support, as shown in its row
export interface SupportValues {
  recipient: DeepReadonly<Entity> | null
  agents: DeepReadonly<Entity>[]
  amount: number | null
  currency: string | null
  dates: Record<DateFieldName, DateWithPrecision | null>
}

// Another saved support shown under a row: one of its possible duplicates,
// or a match of the new support being edited
export interface SubRow {
  parentId: string
  kind: "duplicate" | "match"
  // The row of the support shown
  otherId: string
  amountDiffers?: boolean
}

export interface SupportRow {
  // The transfer's ID, or `new-<declaration ID>` for a new support, or
  // `<parent ID>><row ID>` for a sub-row
  id: string
  transfer: HubTransfer | null
  // The change of the support, or the new support
  declaration: Declaration | null
  // The pending merges and not-duplicates of the transfer
  reconciliations: Declaration[]
  // The rows of its possible duplicates, not reconciled yet
  duplicateIds: string[]
  group: RowGroup
  // Removed by a change not published yet: faded
  removed: boolean
  sub?: SubRow
  emitter_id: string
  emitter: DeepReadonly<Entity> | undefined
  emitter_sub?: string | null
  recipient_id: string
  recipient: DeepReadonly<Entity> | null
  agent_ids: string[]
  agents: DeepReadonly<Entity>[]
  amount: number | null
  currency: string | null
  amounts_clc: Record<string, number> | null
  // Hidden on the public page
  amount_hidden: boolean
  // Declared in the Hub: not converted into other currencies yet
  unconverted: boolean
  date_clc: DateWithPrecision | null
  // The row being edited: its saved values, which sort it so that it
  // doesn't move
  saved?: SupportRow
}

// The row of the support being added
export const NEW_ROW_ID = "__new"

export function valuesFromTransfer(transfer: HubTransfer): SupportValues {
  return {
    recipient: transfer.recipient ?? null,
    agents: transfer.agents?.filter(Boolean) ?? [],
    amount: transfer.amount,
    currency: transfer.currency,
    dates: Object.fromEntries(
      DATE_FIELDS.map((f) => [f, transfer[f]]),
    ) as SupportValues["dates"],
  }
}

export function valuesFromDeclaration(
  declaration: Declaration,
  getEntity: (id: string) => DeepReadonly<Entity> | undefined,
): SupportValues {
  return {
    recipient: declaration.recipient_id
      ? (getEntity(declaration.recipient_id) ?? null)
      : null,
    agents: declaration.agent_ids
      .map(getEntity)
      .filter((e): e is DeepReadonly<Entity> => !!e),
    amount: declaration.amount,
    currency: declaration.currency,
    dates: Object.fromEntries(
      DATE_FIELDS.map((f) => [f, declaration[f]]),
    ) as SupportValues["dates"],
  }
}

// The values typed, invalid dates left out
export function valuesFromDraft(draft: SupportDraft): SupportValues {
  return {
    recipient: draft.recipient,
    agents: draft.agents,
    amount: draft.amount,
    currency: draft.currency,
    dates: Object.fromEntries(
      DATE_FIELDS.map((f) => [f, parseDateInput(draft.dates[f])]),
    ) as SupportValues["dates"],
  }
}

export function draftFromValues(values: SupportValues): SupportDraft {
  return {
    recipient: values.recipient,
    agents: [...values.agents],
    amount: values.amount,
    amountText: formatAmountInput(values.amount),
    currency: values.currency,
    dates: Object.fromEntries(
      DATE_FIELDS.map((f) => [f, formatDateInput(values.dates[f])]),
    ) as SupportDraft["dates"],
  }
}

export function emptyDraft(currency: string | null): SupportDraft {
  return {
    recipient: null,
    agents: [],
    amount: null,
    amountText: "",
    currency,
    dates: Object.fromEntries(
      DATE_FIELDS.map((f) => [f, ""]),
    ) as SupportDraft["dates"],
  }
}

// The row's columns showing declared values, not yet converted by TSOSI
function declaredColumns(values: SupportValues) {
  return {
    recipient_id: values.recipient?.id ?? "",
    recipient: values.recipient,
    agent_ids: values.agents.map((a) => a.id),
    agents: values.agents,
    amount: values.amount,
    currency: values.currency,
    amounts_clc:
      values.amount != null && values.currency
        ? { [values.currency]: values.amount }
        : null,
    amount_hidden: false,
    unconverted: values.amount != null,
    date_clc: computeDateClc(values.dates)?.date ?? null,
  }
}

// The possible duplicates first, then the changes, then the status
export function rowGroup(
  pending: Declaration[],
  duplicateIds: string[],
  status: RowGroup,
): RowGroup {
  if (duplicateIds.length) {
    return "duplicate"
  }
  if (pending.length) {
    return pending.some((d) => d.status == "draft")
      ? "unpublished"
      : "submitted"
  }
  return status
}

// The data of the supports table, as loaded
export interface SupportTableData {
  // The organization whose Hub it is
  organization: DeepReadonly<Entity>
  transfers: HubTransfer[]
  declarations: Declaration[]
  // The pairs of rows that may be the same support, not reconciled yet
  duplicatePairs: [string, string][]
  getEntity: (id: string) => DeepReadonly<Entity> | undefined
}

// The saved rows of the supports table, and their indexes
export interface SupportTable extends SupportTableData {
  transferById: Map<string, HubTransfer>
  // The pending change of each transfer
  changeByTransfer: Map<string, Declaration>
  // The pending merges and not-duplicates of each transfer
  reconciliationsByTransfer: Map<string, Declaration[]>
  // The possible duplicates of each row
  duplicatesByRow: Map<string, string[]>
  // The new supports, then the transfers
  rows: SupportRow[]
  rowById: Map<string, SupportRow>
}

function groupBy<T>(entries: [string, T][]): Map<string, T[]> {
  const result = new Map<string, T[]>()
  for (const [key, value] of entries) {
    result.set(key, [...(result.get(key) ?? []), value])
  }
  return result
}

export function buildSupportTable(data: SupportTableData): SupportTable {
  const table: SupportTable = {
    ...data,
    transferById: new Map(data.transfers.map((t) => [t.id, t])),
    changeByTransfer: new Map(
      data.declarations
        .filter((d) => SUPPORT_CHANGE_KINDS.includes(d.kind))
        .map((d) => [d.transfer_id!, d]),
    ),
    reconciliationsByTransfer: groupBy(
      data.declarations
        .filter((d) => RECONCILIATION_KINDS.includes(d.kind))
        .flatMap((d) =>
          [d.transfer_id!, ...d.other_transfer_ids].map(
            (id) => [id, d] as [string, Declaration],
          ),
        ),
    ),
    duplicatesByRow: groupBy(
      data.duplicatePairs.flatMap(([left, right]) => [
        [left, right],
        [right, left],
      ]),
    ),
    rows: [],
    rowById: new Map(),
  }
  table.rows = [
    ...data.declarations
      .filter((d) => d.kind == "new")
      .map((d) =>
        newSupportRow(
          table,
          newRowId(d.id),
          valuesFromDeclaration(d, data.getEntity),
          d,
        ),
      ),
    ...data.transfers.map((t) => transferRow(table, t)),
  ]
  table.rowById = new Map(table.rows.map((row) => [row.id, row]))
  return table
}

function transferRow(table: SupportTable, transfer: HubTransfer): SupportRow {
  const declaration = table.changeByTransfer.get(transfer.id) ?? null
  const reconciliations = table.reconciliationsByTransfer.get(transfer.id) ?? []
  const duplicateIds = table.duplicatesByRow.get(transfer.id) ?? []
  const pending = [...(declaration ? [declaration] : []), ...reconciliations]
  const row: SupportRow = {
    id: transfer.id,
    transfer,
    declaration,
    reconciliations,
    duplicateIds,
    group: rowGroup(pending, duplicateIds, transfer.status),
    removed: declaration?.kind == "removal",
    emitter_id: transfer.emitter_id,
    emitter: transfer.emitter,
    emitter_sub: transfer.emitter_sub,
    recipient_id: transfer.recipient_id,
    recipient: transfer.recipient ?? null,
    agent_ids: transfer.agent_ids,
    agents: transfer.agents ?? [],
    amount: transfer.amount,
    currency: transfer.currency,
    amounts_clc: transfer.amounts_clc ?? null,
    amount_hidden: transfer.amount_hidden,
    unconverted: false,
    date_clc: transfer.date_clc,
  }
  if (declaration?.kind == "edit") {
    Object.assign(
      row,
      declaredColumns(valuesFromDeclaration(declaration, table.getEntity)),
    )
  }
  return row
}

// The row of a new support: a draft, or the values of the one being added
function newSupportRow(
  table: SupportTable,
  id: string,
  values: SupportValues,
  declaration: Declaration | null,
): SupportRow {
  const duplicateIds = table.duplicatesByRow.get(id) ?? []
  return {
    id,
    transfer: null,
    declaration,
    reconciliations: [],
    duplicateIds,
    group: rowGroup(
      declaration ? [declaration] : [],
      duplicateIds,
      "unpublished",
    ),
    removed: false,
    emitter_id: table.organization.id,
    emitter: table.organization,
    ...declaredColumns(values),
  }
}

// The row being edited and its matches, and the row whose possible
// duplicates are shown
export interface RowsState {
  editing: {
    rowId: string
    // The values typed
    values: SupportValues
    // For a new support: the saved supports it may be
    matches: Match[]
  } | null
  openDuplicates: string | null
}

function subRow(
  other: SupportRow,
  parentId: string,
  kind: SubRow["kind"],
  amountDiffers?: boolean,
): SupportRow {
  return {
    ...other,
    id: `${parentId}>${other.id}`,
    sub: { parentId, kind, otherId: other.id, amountDiffers },
    saved: undefined,
  }
}

// The sub-rows under a row: the matches of the new support being edited, or
// its possible duplicates, when shown. Only those of the table's rows.
function subRows(
  table: SupportTable,
  rowId: string,
  state: RowsState,
): SupportRow[] {
  const { rowById } = table
  if (state.editing?.rowId == rowId) {
    return state.editing.matches
      .filter((m) => rowById.has(m.row_id))
      .map((m) =>
        subRow(rowById.get(m.row_id)!, rowId, "match", m.amount_differs),
      )
  }
  if (state.openDuplicates == rowId) {
    return (rowById.get(rowId)?.duplicateIds ?? [])
      .filter((id) => rowById.has(id))
      .map((id) => subRow(rowById.get(id)!, rowId, "duplicate"))
  }
  return []
}

// The rows, the one being edited showing the values typed, each followed by
// its sub-rows
export function tableRows(table: SupportTable, state: RowsState): SupportRow[] {
  const editing = state.editing
  return table.rows.flatMap((row) => [
    row.id == editing?.rowId
      ? { ...row, ...declaredColumns(editing.values), saved: row }
      : row,
    ...subRows(table, row.id, state),
  ])
}

// The row of the support being added, and its matches
export function addedRows(table: SupportTable, state: RowsState): SupportRow[] {
  if (state.editing?.rowId != NEW_ROW_ID) {
    return []
  }
  return [
    newSupportRow(table, NEW_ROW_ID, state.editing.values, null),
    ...subRows(table, NEW_ROW_ID, state),
  ]
}

// The rows of a status, with the row being edited or whose possible
// duplicates are shown; the sub-rows with their row
export function filterRows(
  table: SupportTable,
  rows: SupportRow[],
  group: FilterGroup | null,
  state: RowsState,
): SupportRow[] {
  if (!group) {
    return rows
  }
  const visible = (row: SupportRow) =>
    filterGroup(row) == group ||
    row.id == state.editing?.rowId ||
    row.id == state.openDuplicates
  return rows.filter((row) =>
    row.sub ? visible(table.rowById.get(row.sub.parentId)!) : visible(row),
  )
}

// The number of saved rows of each status of the legend
export function groupCounts(
  rows: SupportRow[],
): Partial<Record<FilterGroup, number>> {
  const counts: Partial<Record<FilterGroup, number>> = {}
  for (const row of rows) {
    const group = filterGroup(row)
    if (group) {
      counts[group] = (counts[group] ?? 0) + 1
    }
  }
  return counts
}

// The sort values of a row: the sub-rows are sorted with their row, just
// after it, and the row being edited doesn't move
export function sortRow(table: SupportTable, row: SupportRow): SupportRow {
  if (row.sub) {
    return table.rowById.get(row.sub.parentId) ?? row
  }
  return row.saved ?? row
}

// The changes referring to supports missing from the table: deleted or
// merged since, e.g. by an ingest
export function orphans(table: SupportTable): Declaration[] {
  const exists = (id: string | null) => !!id && table.transferById.has(id)
  return table.declarations.filter((d) => {
    if (SUPPORT_CHANGE_KINDS.includes(d.kind)) {
      return !exists(d.transfer_id)
    }
    if (RECONCILIATION_KINDS.includes(d.kind)) {
      return !exists(d.transfer_id) || !d.other_transfer_ids.some(exists)
    }
    return false
  })
}

// The organization's last used currency, for new supports
export function defaultCurrency(
  transfers: HubTransfer[],
  organizationId: string,
): string {
  const own = transfers
    .filter((t) => t.emitter_id == organizationId && t.currency)
    .sort((a, b) =>
      (b.date_clc?.value ?? "").localeCompare(a.date_clc?.value ?? ""),
    )
  return own[0]?.currency ?? "EUR"
}

export function isNewRow(row: SupportRow): boolean {
  return !row.transfer && row.declaration?.kind == "new"
}

// Whether the transfer is in a pending merge
function inMerge(table: SupportTable, transferId: string): boolean {
  return (table.reconciliationsByTransfer.get(transferId) ?? []).some(
    (d) => d.kind == "merge",
  )
}

// Whether the row has changes waiting for approval
export function isLocked(row: SupportRow): boolean {
  return [row.declaration, ...row.reconciliations].some(
    (d) => d?.status == "submitted",
  )
}

// Why a row can't be the support entered, or the same as another one: it's
// missing, or has a change waiting for approval that this would change
export function lockedReason(row: SupportRow | undefined): string | undefined {
  if (!row) {
    return "This support doesn't exist any more."
  }
  if (row.declaration?.status == "submitted") {
    return "It has a change waiting for approval."
  }
  return undefined
}

// Why two possible duplicates can't be marked as the same support, or not
export function pairDisabledReasons(
  table: SupportTable,
  left: SupportRow,
  right: SupportRow,
): { same?: string; different?: string } {
  const news = [left, right].filter(isNewRow)
  if (news.length == 0) {
    const merged = inMerge(table, left.id) || inMerge(table, right.id)
    return {
      same: merged
        ? "One of them is already marked as the same as another one."
        : undefined,
    }
  }
  const drafts = news.filter((r) => r.declaration!.status == "draft")
  if (!drafts.length) {
    const reason = "Its change is waiting for approval."
    return { same: reason, different: reason }
  }
  if (news.length == 2) {
    return {}
  }
  // A new support and a published one: the new one becomes its change
  const published = left.transfer ? left : right
  return { same: lockedReason(published) }
}

// The saved supports that a draft new support was declared not to be
export function dismissedRows(declaration: Declaration | null): string[] {
  if (!declaration) {
    return []
  }
  return [
    ...declaration.other_transfer_ids,
    ...declaration.other_declaration_ids.map(newRowId),
  ]
}

// The transfers that a reconciliation says the transfer is, or isn't
function reconciledWith(declaration: Declaration, transferId: string) {
  return declaration.transfer_id == transferId
    ? declaration.other_transfer_ids
    : [declaration.transfer_id!]
}

function rowLabel(table: SupportTable, id: string): string {
  const row = table.rowById.get(id)
  return row ? supportLabel(row) : "a support"
}

// What's pending on the row, and its possible duplicates, one per item
export function rowNotes(table: SupportTable, row: SupportRow): string[] {
  if (row.sub) {
    return []
  }
  const notes: string[] = []
  const state = (d: Declaration) =>
    d.status == "submitted" ? "waiting for approval" : "not published"
  if (row.declaration && row.transfer) {
    const kind = KIND_LABELS[row.declaration.kind]
    notes.push(`${kind} (${state(row.declaration)})`)
  }
  for (const reconciliation of row.reconciliations) {
    const others = reconciledWith(reconciliation, row.id)
      .map((id) => rowLabel(table, id))
      .join("; ")
    notes.push(
      reconciliation.kind == "merge"
        ? `The same support as ${others} (${state(reconciliation)})`
        : `Not the same support as ${others} (${state(reconciliation)})`,
    )
  }
  for (const id of row.duplicateIds) {
    notes.push(`May be the same support as ${rowLabel(table, id)}`)
  }
  return notes
}
