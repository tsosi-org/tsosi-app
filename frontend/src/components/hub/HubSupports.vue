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
import { useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import SupportCellEditor from "@/components/hub/SupportCellEditor.vue"
import SupportRowPanel from "@/components/hub/SupportRowPanel.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { originalCurrency, selectedCurrency } from "@/singletons/currencyStore"
import {
  EDITOR_FIELD_ERRORS,
  getDeclarations,
  getSubmissions,
  KIND_LABELS,
  type Declaration,
  type DeclarationErrors,
  type EditorField,
  type Submission,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import { recipientScope, scopeHighlight } from "@/singletons/hub-organizations"
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
import {
  draftErrors,
  draftPayloadValues,
  errorMessage,
  errorMessages,
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
  draftFromValues,
  emptyDraft,
  NEW_ROW_ID,
  orphans,
  pairDisabledReasons,
  ROW_STATUSES,
  sortRow,
  statusInfo,
  tableRows,
  valuesFromDeclaration,
  valuesFromDraft,
  valuesFromTransfer,
  type RowsState,
  type SubRow,
  type SupportRow,
} from "@/utils/hub-support-rows"
import { hiddenTransferColumns, transferColumns } from "@/utils/transfer-table"
import { getHubEntityRef } from "@/utils/url-utils"

/**
 * The organization's supports table in the Hub: the transfers declared about
 * it, merged with its changes not published yet (declarations), which members
 * prepare here, reconcile with the saved ones, and submit.
 * A row is edited in place: its cells become inputs, but its dates, typed in
 * a panel under it. The possible duplicates of a row, found once it's saved,
 * show as sub-rows under it.
 * The rows are built by `hub-support-rows`, the changes saved by
 * `hub-support-changes`: this component holds the state and renders it.
 * The table's filters, its status' included, are in the URL, like its sort
 * and page. Escape cancels the row being edited or added.
 */
const props = defineProps<{
  organization: DeepReadonly<EntityDetails>
  // The TSOSI team on an organization's Hub
  readOnly: boolean
}>()

const router = useRouter()
const root = useTemplateRef<HTMLElement>("root")

// The fields edited in their cell: the dates in the panel under the row,
// the currency with the amount
type CellField = Exclude<EditorField, "date" | "currency">

const editableColumns: Record<string, EditorField> = {
  date_clc: "date",
  agents: "agents",
  recipient: "recipient",
  amount: "amount",
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
  // The organization being added, for the beneficiary or an intermediary,
  // from the text searched
  adding: { field: "agents" | "recipient"; name: string } | null
  errors: DeclarationErrors
  saving: boolean
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
    },
    openDuplicates: openDuplicates.value,
  }
})

const rows = computed(() => tableRows(table.value, rowsState.value))
// The new support being added
const newRows = computed(() => addedRows(table.value, rowsState.value))

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

const COLUMN_WIDTHS: Record<string, string | undefined> = {
  date_clc: "9rem",
  emitterCountry: "8rem",
  amount: "16rem",
  status: "10rem",
}

// The amount shown and its currency: in the selected currency once
// converted, else in its own, e.g. until TSOSI converts an amount declared
function shownAmount(row: SupportRow): {
  amount: number | null
  currency: string | null
} {
  if (row.amount == null) {
    return { amount: null, currency: null }
  }
  const selected = selectedCurrency.value.id
  const converted = row.unconverted ? null : row.amounts_clc?.[selected]
  return converted != null
    ? { amount: converted, currency: selected }
    : { amount: row.amount, currency: row.currency }
}

function hubColumns(): TableColumnProps[] {
  // Without the columns' explanations
  const columns = transferColumns().map<TableColumnProps>((column) => ({
    ...column,
    info: undefined,
  }))
  // The full dates declared, not only their year
  columns.find((c) => c.id == "date_clc")!.fullDate = true
  // The amount declared in the Hub, its currency next to it when it's not
  // the selected one, as on the public page
  const amount = columns.find((c) => c.id == "amount")!
  Object.assign(amount, {
    labelGetter: (row: SupportRow) => shownAmount(row).amount,
    labelSuffix: (row: SupportRow) => {
      const { currency } = shownAmount(row)
      return currency != selectedCurrency.value.id ? currency : null
    },
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
  // Only in the exports
  columns.find((c) => c.id == "currency")!.labelGetter = (row) =>
    shownAmount(row as SupportRow).currency ?? ""
  // The beneficiaries whose supports aren't public
  const recipient = columns.find((c) => c.id == "recipient")!
  recipient.highlightGetter = (row) => {
    const entity = (row as SupportRow).recipient
    return entity ? scopeHighlight(recipientScope(entity)) : null
  }
  columns.push(statusColumn())
  // Fixed widths, whatever is shown or typed: the organizations share the
  // rest
  for (const column of columns) {
    column.width = COLUMN_WIDTHS[column.id]
  }
  return columns
}

// The status of the row, a tag explained on hover, and its filter. The
// sub-rows show their own status, but are filtered by their row's, to be
// shown with it.
function statusColumn(): TableColumnProps {
  return {
    id: "status",
    title: "Status",
    field: "status",
    type: "string",
    sortable: true,
    labelGetter: (row) => {
      const sub = (row as SupportRow).sub
      const status = sub
        ? table.value.rowById.get(sub.parentId)?.status
        : (row as SupportRow).status
      return status ? ROW_STATUSES[status].label : ""
    },
    tagGetter: (row) => {
      const status = (row as SupportRow).status
      return status
        ? {
            label: ROW_STATUSES[status].label,
            tooltip: statusInfo(table.value, row as SupportRow),
          }
        : null
    },
    filter: {
      enable: true,
      options: Object.values(ROW_STATUSES).map((s) => s.label),
    },
  }
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

// The possible duplicates of the row whose duplicates are shown: under it,
// and in the rest of the table
const shownDuplicates = computed(
  () =>
    new Set(
      openDuplicates.value
        ? (table.value.rowById.get(openDuplicates.value)?.duplicateIds ?? [])
        : [],
    ),
)

function rowClass(row: SupportRow): string {
  if (row.sub) {
    return "support-row sub-row duplicate-match"
  }
  const classes = ["support-row"]
  if (shownDuplicates.value.has(row.id)) {
    classes.push("duplicate-match")
  }
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
  if (!field || !customCell(row, column) || field == "date") {
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

// The row being edited has a panel under it: its dates, the organization
// being added, or the errors
const panelOpen = computed(
  () =>
    !!editing.value &&
    (editing.value.dateOpen ||
      !!editing.value.adding ||
      rowErrors.value.length > 0),
)

// The table's callbacks get its rows as plain records. Created once: new
// ones at each render remount the table's cells, so the inputs being typed
// in would lose the focus.
type Row = Record<string, any>
const rowCallbacks = {
  rowClass: (row: Row) => rowClass(row as SupportRow),
  cellClass: (row: Row, column: TableColumnProps) =>
    cellClass(row as SupportRow, column),
  customCell: (row: Row, column: TableColumnProps) =>
    customCell(row as SupportRow, column),
  sortRow: (row: Row) => sortRow(table.value, row as SupportRow),
}

const defaultSort = { sortField: "date_clc", sortOrder: -1 as const }
// The actions' buttons wrap in their column. Created once, like the
// callbacks.
const fixedLayout = { minWidth: "66rem", actionsWidth: "12rem" }

const tableProps = computed(() => ({
  id: `${props.organization.id}-hub-supports`,
  data: rows.value,
  // The new support being added, first
  frozenData: newRows.value,
  columns: columns.value,
  defaultSort,
  rowUniqueId: "id",
  urlState: true,
  exportTitle: `TSOSI_Hub_${props.organization.name.replace(/\s+/g, "_")}`,
  ...rowCallbacks,
  expandedRowId: panelOpen.value ? editing.value!.rowId : null,
  fixedLayout,
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
  // In red, e.g. possible duplicates to reconcile
  danger?: boolean
  primary?: boolean
  // Why it can't be used
  disabledReason?: string
}

function rowActions(row: SupportRow): RowAction[] {
  const current = editing.value
  if (current?.rowId == row.id) {
    return editingActions
  }
  if (row.sub) {
    return duplicateActions(row.sub)
  }
  const actions: RowAction[] = []
  // First, in red: they're to be reconciled
  if (row.duplicateIds.length) {
    const open = openDuplicates.value == row.id
    actions.push({
      id: "duplicates",
      label: open
        ? "Hide its possible duplicates"
        : "Show its possible duplicates",
      icon: ["fas", "clone"],
      pressed: open,
      danger: true,
      run: () => (openDuplicates.value = open ? null : row.id),
    })
  }
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

// The actions of the row being edited
const editingActions: RowAction[] = [
  {
    id: "cancel",
    label: "Cancel",
    icon: ["fas", "xmark"],
    run: cancelEdit,
  },
  {
    id: "save",
    label: "Save",
    icon: ["fas", "check"],
    primary: true,
    run: save,
  },
]

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

function actionSeverity(action: RowAction): string | undefined {
  if (action.danger) {
    return "danger"
  }
  return action.primary || action.pressed ? undefined : "secondary"
}

function canAct(row: SupportRow): boolean {
  if (props.readOnly) {
    return false
  }
  // While a row is edited, only its actions
  if (editing.value) {
    return row.id == editing.value.rowId
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
  }
}

// Edit a row, the focus on its first cell, or on the invoice date when the
// dates' panel opens with it (`SupportDates`)
async function openEditing(value: Editing) {
  actionError.value = null
  openDuplicates.value = null
  editing.value = value
  if (value.dateOpen) {
    return
  }
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

// A new support starts in the currency selected for the table, or the
// organization's last one when the table shows each support's own
function startAdd() {
  const currency =
    selectedCurrency.value.id == originalCurrency.id
      ? defaultCurrency(transfers.value ?? [], props.organization.id)
      : selectedCurrency.value.id
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

// Escape cancels the row being edited, but first closes the dropdown it's
// pressed in, if open (the search or the currency): caught before the cells
// stop it
function onEscape(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (
    !editing.value ||
    target?.closest('[role="combobox"][aria-expanded="true"]')
  ) {
    return
  }
  event.preventDefault()
  cancelEdit()
}

// The organization being added from its name is no longer, once another one
// is picked for its cell, e.g. in the search
watch(
  () => {
    const draft = editing.value?.draft
    return draft && [draft.recipient?.id, draft.agents.map((a) => a.id).join()]
  },
  (ids, previous) => {
    const current = editing.value
    if (!current?.adding || !ids || !previous) {
      return
    }
    const index = current.adding.field == "recipient" ? 0 : 1
    if (ids[index] != previous[index]) {
      current.adding = null
    }
  },
)

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

// A new support, being added or a draft: once saved, it's reconciled with
// the saved supports it may be (possible duplicates)
function isNewSupport(current: Editing): boolean {
  return current.rowId == NEW_ROW_ID || current.row?.declaration?.kind == "new"
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
  const draft = current.row?.declaration ?? null
  const values = draftPayloadValues(current.draft)
  let operations: Operations
  if (isNewSupport(current)) {
    operations = newSupportOperations(table.value, draft, values)
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
    @keydown.esc.capture="onEscape"
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
          :field="editableColumns[column.id] as CellField"
          :organizationId="props.organization.id"
          :errors="editing.errors"
          :key="`${data.id}-${column.id}`"
          @addOrganization="
            (field, name) => (editing!.adding = { field, name })
          "
          @focus="editing.dateOpen = false"
        />
      </template>
      <template #actions="{ data }">
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
            :severity="actionSeverity(action)"
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
          :adding="editing.adding"
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
  justify-content: flex-end;
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

/* The buttons of a row, laid out by the table's buttons cell */
.row-actions {
  display: contents;
}

/* They wrap in the fixed width of their column */
.hub-supports :deep(.row-buttons) {
  flex-wrap: wrap;
}

.empty {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
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

/* The possible duplicates of the row whose duplicates are shown, under it
   and in the rest of the table */
.hub-supports :deep(tr.duplicate-match) {
  background: var(--p-red-50);
}

/* A choice picked among the row's actions */
.hub-supports :deep(.row-buttons .p-button.pressed) {
  box-shadow: inset 0 0 0 1px var(--p-primary-color);
}

.hub-supports :deep(.row-buttons .p-button-danger.pressed) {
  box-shadow: inset 0 0 0 2px var(--p-red-800);
}

/* While a row is edited or added, the rest of the table fades: the other
   rows, the headers and the filter, but the row's panel */
.hub-supports :deep(:is(thead, tr.support-row, .p-paginator)) {
  transition: opacity 0.15s;
}

.hub-supports.is-editing
  :deep(:is(thead, tr.support-row:not(.row-editing), .p-paginator)) {
  opacity: 0.4;
}

/* All the rows the height of a row with its buttons, so that they keep it
   while a row is edited, which hides the other rows' buttons */
.hub-supports :deep(tr.support-row > td) {
  height: 3.95rem;
}

/* The currency selector next to the Amount title takes the rest of the
   header */
.hub-supports :deep(.header-currency-selector) {
  flex: 1;
  min-width: 0;

  & .p-select {
    width: 100%;
  }

  /* Compact, to show the code with little room */
  & .p-select-label {
    padding-inline: 0.5rem 0;
  }

  & .p-select-dropdown {
    width: 1.75rem;
  }
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
