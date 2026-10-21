<script setup lang="ts">
import Button from "primevue/button"
import {
  computed,
  nextTick,
  onMounted,
  reactive,
  ref,
  useTemplateRef,
  watch,
} from "vue"
import { useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import SupportCellEditor from "@/components/hub/SupportCellEditor.vue"
import SupportRowPanel from "@/components/hub/SupportRowPanel.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { originalCurrency, selectedCurrency } from "@/singletons/currencyStore"
import {
  EDITOR_FIELD_ERRORS,
  findMatches,
  getDeclarations,
  getSubmissions,
  KIND_LABELS,
  NONE,
  type Declaration,
  type DeclarationErrors,
  type EditorField,
  type Match,
  type Submission,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import {
  recipientScope,
  SCOPE_INFOS,
  SCOPE_LABELS,
  SCOPE_SEVERITIES,
} from "@/singletons/hub-organizations"
import {
  getEntitySummary,
  getHubTransfers,
  type DeepReadonly,
  type Entity,
  type EntityDetails,
  type HubTransfer,
} from "@/singletons/ref-data"
import {
  formatDateWithPrecision,
  formatDateWithPrecisionObj,
} from "@/utils/data-utils"
import debounce from "@/utils/debounce"
import {
  draftErrors,
  draftPayloadValues,
  errorMessage,
  errorMessages,
  matchQuery,
  newSupportOperations,
  reconcileOperations,
  runOperations,
  saveErrors,
  supportOperations,
  type Operations,
} from "@/utils/hub-support-changes"
import {
  addedRows,
  buildSupportTable,
  defaultCurrency,
  dismissedRows,
  draftFromValues,
  emptyDraft,
  filterRows,
  groupCounts,
  isLocked,
  lockedReason,
  NEW_ROW_ID,
  orphans,
  pairDisabledReasons,
  rowNotes,
  sortRow,
  tableRows,
  valuesFromDeclaration,
  valuesFromDraft,
  valuesFromTransfer,
  type FilterGroup,
  type RowsState,
  type SubRow,
  type SupportRow,
} from "@/utils/hub-support-rows"
import { queryString, replaceQuery } from "@/utils/url-state"
import { getHubEntityRef } from "@/utils/url-utils"
import {
  hiddenTransferColumns,
  transferColumns,
  transferDetailsButton,
} from "@/utils/transfer-table"

/**
 * The organization's supports table in the Hub: the transfers declared about
 * it, merged with its changes not published yet (declarations), which members
 * prepare here, reconcile with the saved ones, and submit.
 * A row is edited in place: its cells become inputs, but its dates, typed in
 * a panel under it. The possible duplicates of a row, and the matches of a
 * new support, show as sub-rows under it.
 * The rows are built by `hub-support-rows`, the changes saved by
 * `hub-support-changes`: this component holds the state and renders it.
 * The status picked in the legend is in the URL (`?status=`), like the
 * table's sort, filters and page.
 */
const props = defineProps<{
  organization: DeepReadonly<EntityDetails>
  // The TSOSI team on an organization's Hub
  readOnly: boolean
}>()

const route = useRoute()
const router = useRouter()
const root = useTemplateRef<HTMLElement>("root")

const legend: { group: FilterGroup; label: string; info: string }[] = [
  {
    group: "not_confirmed",
    label: "Not confirmed",
    info: "Only other organizations declared this support. Confirm it, or edit it if it's not right.",
  },
  {
    group: "duplicate",
    label: "Possible duplicate",
    info: "Another support of the organization looks like the same one, with the same beneficiary and dates. Show it, and tell whether they're the same support.",
  },
  {
    group: "unpublished",
    label: "Not published",
    info: "A new support, confirmation, edit, removal (faded) or reconciliation made here. Preview and submit it: it's published once approved by the TSOSI team.",
  },
  {
    group: "submitted",
    label: "Waiting for approval",
    info: "A change submitted to the TSOSI team, read-only until it's approved.",
  },
]

const editableColumns: Record<string, EditorField> = {
  date_clc: "date",
  agents: "agents",
  recipient: "recipient",
  amount: "amount",
  currency: "currency",
}

const transfers = ref<HubTransfer[] | null>(null)
const declarations = ref<Declaration[]>([])
// The pairs of rows that may be the same support, not reconciled yet
const duplicatePairs = ref<[string, string][]>([])
// The submissions waiting for approval
const submissions = ref<Submission[]>([])
const otherEntities = ref<Record<string, Entity>>({})
const loadError = ref(false)
// A change being saved from a row's actions
const busy = ref(false)
const actionError = ref<string | null>(null)

interface Editing {
  rowId: string
  row: SupportRow | null
  draft: SupportDraft
  // The dates' panel is open
  dateOpen: boolean
  // The organization being added from its name, for the beneficiary or an
  // intermediary
  adding: { field: "agents" | "recipient"; name: string } | null
  errors: DeclarationErrors
  saving: boolean
  // For a new support: the saved supports it may be, and the one picked,
  // or `NONE`
  matches: Match[]
  matchChoice: string | null
}
const editing = ref<Editing | null>(null)

// The row whose possible duplicates are shown under it
const openDuplicates = ref<string | null>(null)

onMounted(async () => {
  const [transfersResult, declarationsResult, submissionsResult] =
    await Promise.all([
      getHubTransfers(props.organization),
      getDeclarations(props.organization.id),
      getSubmissions(props.organization.id),
    ])
  if (!transfersResult || !declarationsResult) {
    loadError.value = true
    return
  }
  otherEntities.value = {
    ...transfersResult.entities,
    ...declarationsResult.entities,
  }
  declarations.value = declarationsResult.declarations
  duplicatePairs.value = declarationsResult.duplicates
  submissions.value = submissionsResult ?? []
  transfers.value = transfersResult.transfers
})

async function reloadDeclarations() {
  const result = await getDeclarations(props.organization.id)
  if (!result) {
    actionError.value =
      "The changes couldn't be reloaded. Please reload the page."
    return
  }
  otherEntities.value = { ...otherEntities.value, ...result.entities }
  declarations.value = result.declarations
  duplicatePairs.value = result.duplicates
}

function getEntity(id: string): DeepReadonly<Entity> | undefined {
  return otherEntities.value[id] ?? getEntitySummary(id) ?? undefined
}

// The rows with their saved values
const table = computed(() =>
  buildSupportTable({
    organization: props.organization,
    transfers: transfers.value ?? [],
    declarations: declarations.value,
    duplicatePairs: duplicatePairs.value,
    getEntity,
  }),
)

const rowsState = computed<RowsState>(() => {
  const current = editing.value
  return {
    editing: current && {
      rowId: current.rowId,
      values: valuesFromDraft(current.draft),
      matches: current.matches,
    },
    openDuplicates: openDuplicates.value,
  }
})

const rows = computed(() => tableRows(table.value, rowsState.value))
// The new support being added, and its matches
const newRows = computed(() => addedRows(table.value, rowsState.value))

// The rows of the status picked in the legend, if any
function urlGroup(): FilterGroup | null {
  const status = queryString(route.query, "status")
  return legend.find((item) => item.group == status)?.group ?? null
}
const groupFilter = ref<FilterGroup | null>(urlGroup())
watch(
  () => route.query.status,
  () => (groupFilter.value = urlGroup()),
)
watch(groupFilter, (group) => replaceQuery(router, route, { status: group }))
const counts = computed(() => groupCounts(table.value.rows))
const shownLegend = computed(() =>
  legend.filter((item) => counts.value[item.group]),
)
// Show all the rows again when the picked status has none left, e.g. once
// loaded, from the URL
watch(counts, (value) => {
  if (transfers.value && groupFilter.value && !value[groupFilter.value]) {
    groupFilter.value = null
  }
})

function toggleGroupFilter(group: FilterGroup) {
  groupFilter.value = groupFilter.value == group ? null : group
}

const visibleRows = computed(() =>
  filterRows(table.value, rows.value, groupFilter.value, rowsState.value),
)

// Close the possible duplicates of a row once they're all reconciled
watch(
  () => table.value.rowById,
  (byId) => {
    const id = openDuplicates.value
    if (id && !byId.get(id)?.duplicateIds.length) {
      openDuplicates.value = null
    }
  },
)

const orphanChanges = computed(() => orphans(table.value))

const changesCount = computed(
  () => declarations.value.filter((d) => d.status == "draft").length,
)

function hubColumns(): TableColumnProps[] {
  const columns = transferColumns()
  const amount = columns.find((c) => c.id == "amount")!
  // The amount declared in the Hub, in its own currency until converted
  Object.assign(amount, {
    labelGetter: (row: SupportRow) =>
      row.unconverted || selectedCurrency.value.id == originalCurrency.id
        ? row.amount
        : (row.amounts_clc?.[selectedCurrency.value.id] ?? null),
    nullValueTemplate: undefined,
    info: undefined,
    iconGetter: (row: SupportRow) => {
      if (row.amount_hidden) {
        return {
          icon: ["fas", "eye-slash"],
          tooltip: "Hidden on the public page",
        }
      }
      return null
    },
  })
  // The currency of the amount shown: its own, when not converted yet
  const currency = columns.find((c) => c.id == "currency")!
  currency.labelGetter = (row) => {
    if (row.amount == null) {
      return ""
    }
    if (row.unconverted || selectedCurrency.value.id == originalCurrency.id) {
      return row.currency
    }
    return row.amounts_clc?.[selectedCurrency.value.id] == null
      ? ""
      : selectedCurrency.value.id
  }
  // The beneficiaries whose supports aren't public
  const recipient = columns.find((c) => c.id == "recipient")!
  recipient.tagGetter = (row) => {
    const entity = (row as SupportRow).recipient
    const scope = entity ? recipientScope(entity) : "in_scope"
    if (scope == "in_scope") {
      return null
    }
    return {
      value: SCOPE_LABELS[scope],
      severity: SCOPE_SEVERITIES[scope],
      tooltip: SCOPE_INFOS[scope],
    }
  }
  return columns
}

// All the columns, to fill them, but the supporter's when it's always the
// organization. Only recomputed when the saved data changes.
const columns = computed(() => {
  const hidden = hiddenTransferColumns(props.organization, table.value.rows)
  return hubColumns().filter(
    (c) =>
      !["emitter", "emitterCountry"].includes(c.id) || !hidden.includes(c.id),
  )
})

function rowClass(row: SupportRow): string {
  if (row.sub) {
    const picked =
      row.sub.kind == "match" && editing.value?.matchChoice == row.sub.otherId
    return `support-row sub-row${picked ? " picked" : ""}`
  }
  const classes = ["support-row", `row-${row.group}`]
  if (row.removed) {
    classes.push("row-removed")
  }
  if (row.id == editing.value?.rowId) {
    classes.push("row-editing")
  }
  return classes.join(" ")
}

function fieldHasError(field: EditorField): boolean {
  return EDITOR_FIELD_ERRORS[field].some((key) => editing.value?.errors[key])
}

// The cells of the row being edited are inputs, but the Date cell, a button
// opening the dates' panel
function customCell(row: SupportRow, column: TableColumnProps): boolean {
  return !!editableColumns[column.id] && row.id == editing.value?.rowId
}

function cellClass(row: SupportRow, column: TableColumnProps) {
  const field = editableColumns[column.id]
  if (!customCell(row, column) || field == "date") {
    return undefined
  }
  return fieldHasError(field) ? "inline-cell has-error" : "inline-cell"
}

function toggleDates() {
  editing.value!.dateOpen = !editing.value!.dateOpen
}

// The errors of the row, listed in its panel: its cells only show that
// they're invalid
const rowErrors = computed(() => errorMessages(editing.value?.errors ?? {}))

// An error of a cell not from the server, e.g. an organization that couldn't
// be added
function setCellError(field: EditorField, message: string) {
  editing.value!.errors[EDITOR_FIELD_ERRORS[field][0]] = [message]
}

// The values of each cell, to tell which one changed
function cellValues(draft: SupportDraft): Record<EditorField, string> {
  return {
    date: JSON.stringify(draft.dates),
    agents: draft.agents.map((a) => a.id).join(),
    recipient: draft.recipient?.id ?? "",
    amount: draft.amountText,
    currency: draft.currency ?? "",
  }
}

// The errors of a cell go once it's changed
watch(
  () => editing.value && cellValues(editing.value.draft),
  (values, previous) => {
    const current = editing.value
    if (!current || !values || !previous) {
      return
    }
    for (const field of Object.keys(values) as EditorField[]) {
      if (values[field] != previous[field]) {
        EDITOR_FIELD_ERRORS[field].forEach((key) => delete current.errors[key])
      }
    }
  },
)

// The new support being edited may be one of the saved supports under it:
// the member picks one, or none, before saving
const matchNotice = computed(() => {
  const current = editing.value
  return current?.matches.length && current.matchChoice == null
    ? "This may already be on TSOSI: is it one of the supports below? Pick it (This is it), or None of these."
    : null
})

// The row being edited has a panel under it: its dates, the organization
// being added, the errors, or the notice of its matches
const panelOpen = computed(
  () =>
    !!editing.value &&
    (editing.value.dateOpen ||
      !!editing.value.adding ||
      rowErrors.value.length > 0 ||
      !!matchNotice.value),
)

// The table's callbacks get its rows as plain records. Created once, like
// the buttons: new ones at each render remount the table's cells, so the
// inputs being typed in would lose the focus.
type Row = Record<string, any>
const rowCallbacks = {
  rowClass: (row: Row) => rowClass(row as SupportRow),
  cellClass: (row: Row, column: TableColumnProps) =>
    cellClass(row as SupportRow, column),
  customCell: (row: Row, column: TableColumnProps) =>
    customCell(row as SupportRow, column),
  hideButtons: (row: Row) => !row.transfer?.is_public,
  sortRow: (row: Row) => sortRow(table.value, row as SupportRow),
}

// The "…" button to the page of a public transfer, the sub-rows' included
const buttons = [
  {
    ...transferDetailsButton,
    linkConfig: { ...transferDetailsButton.linkConfig!, suffix: "transfer.id" },
  },
]
const defaultSort = { sortField: "date_clc", sortOrder: -1 as const }

const tableProps = computed(() => ({
  id: `${props.organization.id}-hub-supports`,
  data: visibleRows.value,
  // The new support being added, and its matches, first
  frozenData: newRows.value,
  columns: columns.value,
  defaultSort,
  rowUniqueId: "id",
  buttons,
  urlState: true,
  exportTitle: `TSOSI_Hub_${props.organization.name.replace(/\s+/g, "_")}`,
  ...rowCallbacks,
  expandedRowId: panelOpen.value ? editing.value!.rowId : null,
}))

interface RowAction {
  id: string
  label: string
  icon: [string, string]
  run: () => void
  // Shown with its label
  text?: string
  // A choice: pressed when picked
  pressed?: boolean
  primary?: boolean
  // Why it can't be used
  disabledReason?: string
}

function rowActions(row: SupportRow): RowAction[] {
  const current = editing.value
  if (current?.rowId == row.id) {
    return editingActions(current)
  }
  if (row.sub?.kind == "match") {
    return [matchAction(row.sub)]
  }
  if (row.sub) {
    return duplicateActions(row.sub)
  }
  const actions: RowAction[] = []
  const declaration = row.declaration
  if (declaration?.status != "submitted") {
    actions.push({
      id: "edit",
      label: "Edit",
      icon: ["fas", "pen"],
      run: () => startEdit(row),
    })
  }
  if (declaration?.status == "draft") {
    actions.push({
      id: "undo",
      label: "Undo the change",
      icon: ["fas", "rotate-left"],
      run: () => undo(declaration, row.id),
    })
  } else if (!declaration && row.transfer?.status == "not_confirmed") {
    actions.push({
      id: "confirm",
      label: "Confirm",
      icon: ["fas", "check"],
      run: () => declare(row, "confirmation"),
    })
  } else if (!declaration && row.transfer) {
    actions.push({
      id: "remove",
      label: "Remove this support",
      icon: ["fas", "trash"],
      run: () => declare(row, "removal"),
    })
  }
  if (row.duplicateIds.length) {
    const open = openDuplicates.value == row.id
    actions.push({
      id: "duplicates",
      label: open
        ? "Hide its possible duplicates"
        : "Show its possible duplicates",
      icon: ["fas", "clone"],
      pressed: open,
      run: () => (openDuplicates.value = open ? null : row.id),
    })
  }
  for (const reconciliation of row.reconciliations) {
    if (reconciliation.status == "draft") {
      actions.push({
        id: `undo-${reconciliation.id}`,
        label:
          reconciliation.kind == "merge"
            ? "Undo: marked as the same support"
            : "Undo: marked as different supports",
        icon: ["fas", "rotate-left"],
        run: () => undo(reconciliation, row.id),
      })
    }
  }
  return actions
}

function editingActions(current: Editing): RowAction[] {
  const actions: RowAction[] = []
  if (current.matches.length) {
    actions.push({
      id: "none",
      label: "None of the supports below: it's a new support",
      text: "None of these",
      icon: ["fas", "ban"],
      pressed: current.matchChoice == NONE,
      run: () => pickMatch(NONE),
    })
  }
  actions.push(
    {
      id: "cancel",
      label: "Cancel",
      text: "Cancel",
      icon: ["fas", "xmark"],
      run: cancelEdit,
    },
    {
      id: "save",
      label: "Save",
      text: "Save",
      icon: ["fas", "check"],
      primary: true,
      run: save,
    },
  )
  return actions
}

function matchAction(sub: SubRow): RowAction {
  return {
    id: "match",
    label: sub.amountDiffers
      ? "This is the support entered: your amount is published"
      : "This is the support entered",
    text: "This is it",
    icon: ["fas", "check"],
    pressed: editing.value?.matchChoice == sub.otherId,
    disabledReason: lockedReason(table.value.rowById.get(sub.otherId)),
    run: () => pickMatch(sub.otherId),
  }
}

function duplicateActions(sub: SubRow): RowAction[] {
  const parent = table.value.rowById.get(sub.parentId)!
  const other = table.value.rowById.get(sub.otherId)!
  const reasons = pairDisabledReasons(table.value, parent, other)
  return [
    {
      id: "same",
      label: "The same support",
      text: "Same",
      icon: ["fas", "equals"],
      disabledReason: reasons.same,
      run: () => reconcile(parent, other, true),
    },
    {
      id: "different",
      label: "Not the same support",
      text: "Not the same",
      icon: ["fas", "not-equal"],
      disabledReason: reasons.different,
      run: () => reconcile(parent, other, false),
    },
  ]
}

function canAct(row: SupportRow): boolean {
  if (props.readOnly) {
    return false
  }
  // While a row is edited, only its actions and those of its matches
  if (editing.value) {
    return row.id == editing.value.rowId || row.sub?.kind == "match"
  }
  return true
}

function actionDisabled(action: RowAction, row: SupportRow): boolean {
  if (action.disabledReason) {
    return true
  }
  if (editing.value) {
    return editing.value.saving && action.id != "cancel"
  }
  return busy.value || !canAct(row)
}

function escapeHtml(text: string): string {
  const element = document.createElement("span")
  element.textContent = text
  return element.innerHTML
}

function notesOf(row: SupportRow): string[] {
  return rowNotes(table.value, row)
}

// The notes of the row, one per line, as the HTML of a tooltip
function notesTooltip(row: SupportRow): string {
  return notesOf(row).map(escapeHtml).join("<br>")
}

/**
 * Keep the keyboard focus in the table when the buttons it was on are
 * replaced, e.g. Edit by Save once clicked: on the row's first action, else
 * on the button adding a support.
 */
async function focusRow(rowId?: string) {
  await nextTick()
  const actions = rowId
    ? root.value?.querySelector(`[data-row-id="${rowId}"]`)
    : null
  const target =
    actions?.querySelector<HTMLElement>("button:not(:disabled)") ??
    root.value?.querySelector<HTMLElement>(".add-support")
  target?.focus()
}

function newEditing(
  rowId: string,
  row: SupportRow | null,
  draft: SupportDraft,
): Editing {
  return {
    rowId,
    row,
    draft: reactive(draft),
    // The dates of a new support are required
    dateOpen: !row?.transfer,
    adding: null,
    errors: {},
    saving: false,
    matches: [],
    matchChoice: null,
  }
}

// Edit a row, the focus on its first cell
async function openEditing(value: Editing) {
  actionError.value = null
  openDuplicates.value = null
  editing.value = value
  await nextTick()
  root.value?.querySelector<HTMLElement>(".date-cell")?.focus()
}

function startEdit(row: SupportRow) {
  const declared =
    row.declaration?.kind == "new" || row.declaration?.kind == "edit"
  const values = declared
    ? valuesFromDeclaration(row.declaration!, getEntity)
    : valuesFromTransfer(row.transfer!)
  openEditing(newEditing(row.id, row, draftFromValues(values)))
}

function startAdd() {
  const currency = defaultCurrency(transfers.value ?? [], props.organization.id)
  openEditing(newEditing(NEW_ROW_ID, null, emptyDraft(currency)))
}

function closeEditing() {
  const rowId = editing.value?.rowId
  editing.value = null
  focusRow(rowId)
}

function cancelEdit() {
  closeEditing()
}

function onOrganizationAdded(entity: Entity) {
  const current = editing.value!
  if (current.adding?.field == "recipient") {
    current.draft.recipient = entity
  } else {
    // It replaces the intermediary, as picked in the search (one at most)
    current.draft.agents = [entity]
  }
  current.adding = null
}

// A new support, being added or a draft: it's reconciled with the saved
// supports it may be
function isNewSupport(current: Editing): boolean {
  return current.rowId == NEW_ROW_ID || current.row?.declaration?.kind == "new"
}

// The values of the new support being edited, to find its matches
const currentMatchQuery = computed<string | null>(() => {
  const current = editing.value
  if (!current || !isNewSupport(current)) {
    return null
  }
  return matchQuery(current.draft, current.row?.id ?? null)
})

function setMatches(matches: Match[]) {
  const current = editing.value!
  // Only the supports of the table can be picked
  matches = matches.filter((m) => table.value.rowById.has(m.row_id))
  const ids = (list: Match[]) => list.map((m) => m.row_id).join()
  if (ids(matches) != ids(current.matches)) {
    current.matchChoice = null
    // A draft already declared as none of these
    const dismissed = dismissedRows(current.row?.declaration ?? null)
    if (matches.length && matches.every((m) => dismissed.includes(m.row_id))) {
      current.matchChoice = NONE
    }
  }
  current.matches = matches
}

// The values whose matches are shown
let matchedQuery: string | null = null

async function updateMatches(query: string) {
  const matches = await findMatches(props.organization.id, JSON.parse(query))
  // Only the matches of the values still typed
  if (editing.value && currentMatchQuery.value == query) {
    setMatches(matches ?? [])
    matchedQuery = query
  }
}

const debouncedUpdateMatches = debounce(updateMatches, 400)

watch(currentMatchQuery, (query) => {
  if (query) {
    debouncedUpdateMatches(query)
  } else if (editing.value) {
    setMatches([])
    matchedQuery = null
  }
})

function pickMatch(choice: string) {
  const current = editing.value!
  current.matchChoice = current.matchChoice == choice ? null : choice
  delete current.errors.match
}

async function save() {
  const current = editing.value!
  if (current.saving) {
    return
  }
  // Stopped before saving, e.g. without an amount
  const errors = draftErrors(current.draft)
  if (Object.keys(errors).length) {
    current.errors = errors
    return
  }
  current.saving = true
  // The matches of the values typed last, not found yet
  const query = currentMatchQuery.value
  if (query && query != matchedQuery) {
    await updateMatches(query)
  }
  const draft = current.row?.declaration ?? null
  const values = draftPayloadValues(current.draft)
  let operations: Operations
  if (isNewSupport(current)) {
    if (current.matches.length && current.matchChoice == null) {
      current.errors = {
        match: [
          "This may already be on TSOSI: pick the support below that it is (This is it), or None of these, to save it.",
        ],
      }
      current.saving = false
      return
    }
    operations = newSupportOperations(
      table.value,
      draft,
      values,
      current.matchChoice,
      current.matches.map((m) => m.row_id),
    )
  } else {
    operations = supportOperations(current.row!.transfer!, draft, values)
  }
  const error = await runOperations(props.organization.id, operations)
  // The table as on the server, with the changes saved before an error, if
  // any (C4)
  await reloadDeclarations()
  current.saving = false
  if (!error) {
    closeEditing()
    return
  }
  // The row is gone, e.g. a draft undone by another member: the error shows
  // above the table
  const row = current.row && table.value.rowById.get(current.rowId)
  if (current.row && !row) {
    closeEditing()
    actionError.value = errorMessage(error.data)
    return
  }
  // Its declaration as saved, for the next try
  current.row = row ?? null
  current.errors = saveErrors(error)
  if (fieldHasError("date")) {
    current.dateOpen = true
  }
}

// Run the changes of a row's action, then put the focus back on the row
async function act(operations: Operations, rowId?: string) {
  busy.value = true
  actionError.value = null
  const error = await runOperations(props.organization.id, operations)
  if (error) {
    actionError.value = errorMessage(error.data)
  }
  await reloadDeclarations()
  busy.value = false
  focusRow(rowId)
}

function declare(row: SupportRow, kind: "confirmation" | "removal") {
  return act(
    {
      saves: [{ payload: { kind, transfer_id: row.transfer!.id } }],
      deletions: [],
    },
    row.id,
  )
}

function undo(declaration: Declaration, rowId?: string) {
  return act({ saves: [], deletions: [declaration] }, rowId)
}

function reconcile(parent: SupportRow, other: SupportRow, same: boolean) {
  return act(reconcileOperations(table.value, parent, other, same), parent.id)
}

function formatSubmissionDate(submission: Submission): string {
  return formatDateWithPrecision(submission.consent_at, "day") ?? ""
}

function openSubmit() {
  router.push({
    name: "hub-submit",
    params: { entityId: getHubEntityRef(props.organization) },
  })
}
</script>

<template>
  <Message v-if="loadError" severity="error">
    The supports couldn't be loaded. Please try again later.
  </Message>
  <Loader v-else-if="!transfers" width="100px"></Loader>
  <div
    v-else
    ref="root"
    class="hub-supports"
    :class="{ 'is-editing': !!editing }"
  >
    <Message
      v-for="submission of submissions"
      :key="submission.id"
      severity="info"
    >
      <strong>Submission waiting for approval by the TSOSI team.</strong>
      Sent on {{ formatSubmissionDate(submission) }}
      <template v-if="submission.submitted_by">
        by {{ submission.submitted_by }}</template
      >, with {{ submission.changes_count }}
      {{ submission.changes_count == 1 ? "change" : "changes" }}. They're
      read-only until approved. You can keep preparing new changes: they'll go
      into your next submission.
    </Message>
    <div v-if="!props.readOnly" class="supports-toolbar">
      <Button
        :label="`Preview and submit (${changesCount} ${changesCount == 1 ? 'change' : 'changes'})`"
        severity="secondary"
        :disabled="!changesCount || !!editing"
        @click="openSubmit"
      >
        <template #icon>
          <font-awesome-icon :icon="['fas', 'paper-plane']" />
        </template>
      </Button>
    </div>
    <Message v-if="actionError" severity="error" closable>
      {{ actionError }}
    </Message>
    <Message v-if="orphanChanges.length" severity="warn">
      <p class="orphans-title">
        These changes refer to supports that changed since, e.g. merged with
        another one by a new dataset. Undo them, and make them again on the
        supports below if needed.
      </p>
      <ul class="orphans">
        <li v-for="orphan of orphanChanges" :key="orphan.id">
          {{ KIND_LABELS[orphan.kind] }}
          <Button
            v-if="orphan.status == 'draft' && !props.readOnly"
            label="Undo"
            size="small"
            severity="secondary"
            :disabled="busy"
            @click="undo(orphan)"
          />
          <span v-else-if="orphan.status == 'submitted'" class="hint">
            (waiting for approval: the TSOSI team will return it)
          </span>
        </li>
      </ul>
    </Message>
    <div v-if="shownLegend.length" class="legend">
      <span :id="`${tableProps.id}-legend`" class="legend-title">Filter:</span>
      <ul :aria-labelledby="`${tableProps.id}-legend`">
        <li v-for="item of shownLegend" :key="item.group">
          <button
            type="button"
            class="legend-item"
            :class="[
              `row-${item.group}`,
              { active: groupFilter == item.group },
            ]"
            :aria-pressed="groupFilter == item.group"
            v-tooltip.bottom="item.info"
            @click="toggleGroupFilter(item.group)"
          >
            {{ item.label }}
            <span class="legend-count">{{ counts[item.group] }}</span>
          </button>
        </li>
      </ul>
    </div>

    <p v-if="rows.length == 0 && !newRows.length" class="empty">
      TSOSI doesn't know any support from this organization yet.
      <template v-if="!props.readOnly">
        Add the organization's supports to open science infrastructures:
        <Button
          label="Add a support"
          class="add-support"
          size="small"
          @click="startAdd"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'plus']" />
          </template>
        </Button>
      </template>
    </p>
    <Table v-else v-bind="tableProps">
      <template #actionsHeader>
        <Button
          v-if="!props.readOnly"
          v-tooltip.bottom="'Add a support'"
          aria-label="Add a support"
          class="add-support"
          size="small"
          :disabled="!!editing"
          @click="startAdd"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'plus']" />
          </template>
        </Button>
      </template>
      <template #cell="{ data, column }">
        <button
          v-if="editing && editableColumns[column.id] == 'date'"
          type="button"
          class="editable-cell date-cell"
          :class="{
            selected: editing.dateOpen,
            'has-error': fieldHasError('date'),
          }"
          :aria-label="`Dates: ${formatDateWithPrecisionObj(data.date_clc) || 'none'}`"
          :aria-expanded="editing.dateOpen"
          @click="toggleDates"
        >
          {{ formatDateWithPrecisionObj(data.date_clc) }}
        </button>
        <SupportCellEditor
          v-else-if="editing"
          v-model:draft="editing.draft"
          :field="editableColumns[column.id] as Exclude<EditorField, 'date'>"
          :organizationId="props.organization.id"
          :errors="editing.errors"
          :key="`${data.id}-${column.id}`"
          @addOrganization="
            (field, name) => (editing!.adding = { field, name })
          "
          @focus="editing.dateOpen = false"
          @error="
            (message) => setCellError(editableColumns[column.id], message)
          "
        />
      </template>
      <template #actions="{ data }">
        <span
          v-if="notesOf(data as SupportRow).length"
          v-tooltip.bottom="{
            value: notesTooltip(data as SupportRow),
            escape: false,
          }"
          class="row-icon"
          tabindex="0"
          role="img"
          :aria-label="notesOf(data as SupportRow).join('. ')"
        >
          <font-awesome-icon :icon="['fas', 'circle-info']" />
        </span>
        <span
          v-if="isLocked(data as SupportRow)"
          v-tooltip.bottom="
            'Waiting for approval by the TSOSI team: read-only until then.'
          "
          class="row-icon"
          tabindex="0"
          role="img"
          aria-label="Waiting for approval by the TSOSI team: read-only until then."
        >
          <font-awesome-icon :icon="['fas', 'lock']" />
        </span>
        <span
          v-if="canAct(data as SupportRow)"
          class="row-actions"
          :data-row-id="data.id"
        >
          <Button
            v-for="action of rowActions(data as SupportRow)"
            :key="action.id"
            v-tooltip.bottom="action.disabledReason ?? action.label"
            :aria-label="action.label"
            :aria-pressed="action.pressed"
            :label="action.text"
            :severity="
              action.primary || action.pressed ? undefined : 'secondary'
            "
            :class="{ pressed: action.pressed }"
            :disabled="actionDisabled(action, data as SupportRow)"
            :loading="action.id == 'save' && editing?.saving"
            @click="action.run"
          >
            <template #icon>
              <font-awesome-icon :icon="action.icon" />
            </template>
          </Button>
        </span>
      </template>
      <template #expansion>
        <SupportRowPanel
          v-if="editing"
          v-model:dates="editing.draft.dates"
          :organizationId="props.organization.id"
          :showDates="editing.dateOpen"
          :errors="editing.errors"
          :errorMessages="rowErrors"
          :notice="matchNotice"
          :addingName="editing.adding?.name ?? null"
          @added="onOrganizationAdded"
          @cancelAdd="editing.adding = null"
        />
      </template>
    </Table>
  </div>
</template>

<style scoped>
.hub-supports {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.supports-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
}

.orphans-title {
  margin: 0;
}

.orphans {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin: 0.5rem 0 0;

  & li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
}

.hint {
  margin: 0;
  color: var(--p-neutral-500);
}

.row-icon {
  padding: 0 0.3rem;
  color: var(--p-neutral-500);
}

/* The buttons of a row, laid out by the table's buttons cell */
.row-actions {
  display: contents;
}

.empty {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;

  & ul {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }
}

.legend-title {
  font-weight: 600;
}

/* Like the table's rows: their color, and their top and bottom borders */
.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.8rem;
  border: none;
  border-block: 1px solid var(--p-datatable-body-cell-border-color);
  border-radius: 0;
  background: var(--row-color);
  color: inherit;
  font: inherit;
  cursor: pointer;

  &:hover {
    border-block-color: var(--p-neutral-400);
  }

  &.active {
    border-block-color: var(--p-primary-color);
    box-shadow:
      inset 0 1px 0 var(--p-primary-color),
      inset 0 -1px 0 var(--p-primary-color);
  }
}

.legend-count {
  color: var(--p-neutral-500);
}

/* Row colors, by status. The legend's items use the same classes. */
.hub-supports :deep(.row-not_confirmed) {
  --row-color: var(--p-amber-50);
  --row-accent: var(--p-amber-400);
}

.hub-supports :deep(.row-duplicate) {
  --row-color: var(--p-orange-50);
  --row-accent: var(--p-orange-400);
}

.hub-supports :deep(.row-unpublished) {
  --row-color: var(--p-sky-50);
  --row-accent: var(--p-sky-500);
}

.hub-supports :deep(.row-submitted) {
  --row-color: var(--p-slate-100);
  --row-accent: var(--p-slate-500);
}

/* Confirmed rows have no color */
.hub-supports :deep(tr.support-row) {
  background: var(--row-color, transparent);
}

/* The supports shown under a row, as rows of the table: indented, with a
   mark of the row they're under */
.hub-supports :deep(tr.sub-row) {
  background: var(--p-neutral-50);
}

.hub-supports :deep(tr.sub-row > td:first-child) {
  position: relative;
  padding-left: 2rem;
}

.hub-supports :deep(tr.sub-row > td:first-child)::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 50%;
  left: 0.9rem;
  width: 0.6rem;
  border-left: 2px solid var(--p-neutral-300);
  border-bottom: 2px solid var(--p-neutral-300);
}

/* The match picked */
.hub-supports :deep(tr.sub-row.picked) {
  background: var(--p-primary-50);
  box-shadow:
    inset 0 1px 0 var(--p-primary-color),
    inset 0 -1px 0 var(--p-primary-color);
}

/* A choice picked among the row's actions */
.hub-supports :deep(.row-buttons .p-button.pressed) {
  box-shadow: inset 0 0 0 1px var(--p-primary-color);
}

/* The "…" link button, like the other buttons: over the global link color,
   and without the inherited line height that buttons don't have */
.hub-supports :deep(.row-buttons a.p-button) {
  color: revert-layer;
  line-height: normal;
}

/* While a row is edited or added, the rest of the table fades: the other
   rows, the headers and the filters, but the row's panel and its matches */
.hub-supports :deep(:is(.legend, thead, tr.support-row, .p-paginator)) {
  transition: opacity 0.15s;
}

.hub-supports.is-editing
  :deep(
    :is(
        .legend,
        thead,
        tr.support-row:not(.row-editing, .sub-row),
        .p-paginator
      )
  ) {
  opacity: 0.4;
}

/* Faded, all but the buttons' cell */
.hub-supports :deep(tr.support-row.row-removed > td:not(:last-child)) {
  opacity: 0.5;
}

/* The Date cell, a button opening the dates' panel: all the same height,
   whatever its content */
.editable-cell {
  display: flex;
  align-items: center;
  box-sizing: border-box;
  width: calc(100% + 0.8rem);
  min-height: 2.9rem;
  margin: -0.4rem;
  padding: 0.4rem;
  border: 1px dashed var(--p-neutral-400);
  border-radius: 4px;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid var(--p-primary-color);
    outline-offset: 1px;
  }
}

/* A thicker border with a shadow, so that the cell keeps its size */
.editable-cell.selected {
  border: 1px solid var(--p-primary-color);
  box-shadow: inset 0 0 0 1px var(--p-primary-color);
}

.editable-cell.has-error {
  border-color: var(--p-red-500);
}
</style>
