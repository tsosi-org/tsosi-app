<script setup lang="ts">
import { FilterMatchMode } from "@primevue/core/api"
import Button from "primevue/button"
import Column from "primevue/column"
import DataTable, { type DataTableSortMeta } from "primevue/datatable"
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import Select from "primevue/select"
import Skeleton from "primevue/skeleton"
import {
  computed,
  nextTick,
  onBeforeMount,
  ref,
  useTemplateRef,
  watch,
  type Ref,
} from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import CustomButton, {
  type ButtonProps,
} from "@/components/atoms/ButtonAtom.vue"
import Country from "@/components/atoms/CountryAtom.vue"
import EntityLinkDataAtom from "@/components/atoms/EntityLinkDataAtom.vue"
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import MenuButtonAtom from "@/components/atoms/MenuButtonAtom.vue"
import CurrencySelector from "@/components/CurrencySelector.vue"
import {
  exportCSV,
  exportJSON,
  formatDateWithPrecision,
  formatItemLabel,
  getCountryLabel,
  getEntityLinkRows,
  getItemLabel,
  getItemLink,
  resolveValueFromPath,
  type DataFieldProps,
} from "@/utils/data-utils"
import debounce, { type DebounceStatus } from "@/utils/debounce"
import { queryString, replaceQuery, type QueryValues } from "@/utils/url-state"

interface AppliedFilters {
  [columnId: string]: string
}

export interface CellIcon {
  icon: [string, string]
  tooltip: string
}

// A class and tooltip highlighting the organizations of a cell, e.g. with an
// outline and background color
export interface CellHighlight {
  class: string
  tooltip?: string
}

// A tag in place of the value, explained by its tooltip, e.g. a status
export interface CellTag {
  label: string
  tooltip: string
}

// A line of a cell, with a detail that isn't broken across lines
export interface CellLine {
  text: string
  detail?: string
}

export interface TableColumnProps extends DataFieldProps {
  sortable?: boolean
  sortField?: string // field used to sort the column. Defaults to fieldLabel
  info?: string
  currencySelector?: boolean
  nullValueTemplate?: string
  // Icon with a tooltip displayed after the value, for some rows
  iconGetter?: (item: Record<string, any>) => CellIcon | null
  // Highlight of the organizations of an `entityLink` cell, for some rows
  highlightGetter?: (item: Record<string, any>) => CellHighlight | null
  // Display the value as lines. The label is still used to filter and
  // export the data.
  linesGetter?: (item: Record<string, any>) => CellLine[]
  // Display the value as a tag with a tooltip, for some rows (`CellTag`)
  tagGetter?: (item: Record<string, any>) => CellTag | null
  minWidth?: string
  // Its width with `fixedLayout`, e.g. `8rem`. The columns without one share
  // the rest.
  width?: string
  // Text appended to the displayed value, e.g. the currency of an amount
  // that differs from the selected one.
  labelSuffix?: (item: Record<string, any>) => string | null | undefined
  // Only included in the exports, not displayed in the table.
  exportOnly?: boolean
  // Dates show only their year in tables: show the full date instead
  fullDate?: boolean
  filter?: {
    enable?: boolean
    placeHolder?: string
    // Filter with a select of these values instead of a text search
    options?: string[]
  }
}

export interface TableProps {
  id: string
  data: Array<Record<string, any>>
  // Rows shown first, neither sorted, filtered, paginated nor exported, e.g.
  // a row being added
  frozenData?: Array<Record<string, any>>
  columns: Array<TableColumnProps>
  header?: {
    title: string
  }
  defaultSort?: {
    sortField: string | ((item: any) => any)
    sortOrder: 1 | 0 | -1
  }
  rowUniqueId: string
  skeleton?: boolean
  // Keep the sort, filters and page in the URL: `true`, or the prefix of
  // their params on a page with several tables (see `urlParams`)
  urlState?: boolean | string
  rowSelectable?: boolean
  // The same array across renders: a new one remounts all the cells, e.g.
  // the inputs of `customCell` being typed in
  buttons?: Array<ButtonProps>
  disableExport?: boolean
  exportTitle?: string
  hideCount?: boolean
  // Rows without the buttons, e.g. not saved yet
  hideButtons?: (item: Record<string, any>) => boolean
  rowClass?: (item: Record<string, any>) => string | undefined
  // The row whose `expansion` slot is displayed under it
  expandedRowId?: string | null
  cellClass?: (
    item: Record<string, any>,
    column: TableColumnProps,
  ) => string | undefined
  // The cells displaying the `cell` slot instead of their value, e.g. an
  // input to edit it
  customCell?: (item: Record<string, any>, column: TableColumnProps) => boolean
  // The values a row is sorted by, e.g. its saved values while it's edited,
  // so that it doesn't move. Defaults to the row itself.
  sortRow?: (item: Record<string, any>) => Record<string, any>
  // The columns keep their `width`, whatever their content, e.g. inputs or
  // the rows of the page. The table is at least `fixedLayout.minWidth` wide.
  fixedLayout?: { minWidth: string; actionsWidth?: string }
}
const props = defineProps<TableProps>()
const slots = defineSlots<{
  // Buttons of the row, in the last column before `buttons`
  actions?: (props: { data: Record<string, any> }) => any
  // The header of the actions' column
  actionsHeader?: () => any
  expansion?: (props: { data: Record<string, any> }) => any
  // The content of the cells given by `customCell`
  cell?: (props: { data: Record<string, any>; column: TableColumnProps }) => any
}>()
// Holds the declared filters for the DataTable component
// We handle filtering manually. The important thing is to use our custom
// ref `filterModels` to avoid the component built-in filtering.
const filters: Ref<
  { [id: string]: { value: any; matchMode: "" } } | undefined
> = ref({})
const filterModels: { [id: string]: Ref<string | null | undefined> } = {}
const minDataForFilters = 10
// Holds the applied filters in the form { columnId: filterValue }
const appliedFilters: Ref<{ [columnId: string]: string | null | undefined }> =
  ref({})
const filteredData: Ref<Array<Record<string, any>>> = ref([])
const minWidthWithFilter = "100px"

function columnStyle(column: TableColumnProps): string | undefined {
  if (props.fixedLayout) {
    return column.width ? `width: ${column.width}` : undefined
  }
  if (column.minWidth) {
    return `min-width: ${column.minWidth}`
  }
  return column.filter?.enable ? `min-width: ${minWidthWithFilter}` : undefined
}
const useFilters = computed(
  () => !props.skeleton && props.data.length >= minDataForFilters,
)
const displayedColumns = computed(() =>
  props.columns.filter((c) => !c.exportOnly),
)
const filterStatus: Ref<DebounceStatus> = ref("idle")
// The first row shown, and the number of rows per page
const first = ref(0)
const rows = ref(20)

onBeforeMount(() => {
  // Prepare filters
  populateFilters()
  readUrl()
  applyFilters()
})

// The filters applied last, to go back to the first page when they change
let filtersKey = "{}"

function onFiltersChange() {
  const key = JSON.stringify(getAppliedFilters())
  if (key != filtersKey) {
    filtersKey = key
    first.value = 0
  }
  applyFilters()
  writeUrl()
}

watch(appliedFilters, debounce(onFiltersChange, 250, filterStatus))
watch(() => props.data, applyFilters)
// The first row of the page, the last one when there are fewer rows, e.g.
// from the URL
function clampFirst(value: number): number {
  const pages = Math.ceil(filteredData.value.length / rows.value)
  return Math.min(value, Math.max(0, pages - 1) * rows.value)
}

watch(
  () => filteredData.value.length,
  () => (first.value = clampFirst(first.value)),
)

const expandedRows = computed(() =>
  props.expandedRowId ? { [props.expandedRowId]: true } : {},
)

const route = useRoute()
const router = useRouter()
const tableComponent = useTemplateRef("data-table")
const rowButtonMenu = useTemplateRef("row-button-menu")
const selectedButtonData: Ref<Record<string, any> | null> = ref(null)

// One sort function per column, kept across renders: the DataTable matches
// the sorting to its column by comparing them with `===`
const sortFunctions = new Map<string, (item: Record<string, any>) => any>()

function getSortFieldFunction(columnProps: TableColumnProps) {
  if (!columnProps.sortable) {
    return undefined
  }
  const columnId = columnProps.id
  let sortFunction = sortFunctions.get(columnId)
  if (!sortFunction) {
    // With the column's current props
    sortFunction = (item: Record<string, any>) =>
      getSortValue(
        props.sortRow?.(item) ?? item,
        props.columns.find((c) => c.id == columnId) ?? columnProps,
      )
    sortFunctions.set(columnId, sortFunction)
  }
  return sortFunction
}

function getSortValue(
  item: Record<string, any>,
  columnProps: TableColumnProps,
): any {
  if (columnProps.sortField) {
    return resolveValueFromPath(item, columnProps.sortField)
  } else if (columnProps.type == "country") {
    const country = getItemLabel(item, columnProps)
    return country ? getCountryLabel(country) : null
  } else if (columnProps.type == "dateWithPrecision") {
    // We compare the bare strings for dates as they are correctly formatted
    // as YYYY-MM-DD.
    // Using the computed dateObj does not work with multisorting.
    return resolveValueFromPath(item, columnProps.field + ".value")
  } else if (
    columnProps.type == "entityLink" &&
    columnProps.field == "agents"
  ) {
    return item.agents?.map((a: any) => a.name).join(", ") || null
  }
  return getItemLabel(item, columnProps)
}

// The user's sorting, held here so that new props, like a new `defaultSort`
// object or new columns, don't reset it
const multiSortMeta = ref<DataTableSortMeta[] | undefined>(defaultSortMeta())

function defaultSortMeta(): DataTableSortMeta[] | undefined {
  return props.defaultSort
    ? [
        {
          field: defaultSortFieldFunction(),
          order: props.defaultSort.sortOrder,
        },
      ]
    : undefined
}

function defaultSortFieldFunction() {
  const columnId = props.defaultSort?.sortField
  if (columnId == null) {
    return undefined
  }
  const columns = props.columns.filter((col) => col.id == columnId)
  if (columns.length != 1) {
    return undefined
  }
  return getSortFieldFunction(columns[0])
}

/**
 * The URL's params of the table, prefixed by `urlState` when it's a string:
 * `sort` (column IDs in their sort order, `-` for descending), one
 * `f_<column ID>` per filter, and `page` (from 1). Those of the default
 * state are left out, so that a table with no change has a clean URL.
 */
const urlPrefix = computed(() =>
  typeof props.urlState == "string" ? props.urlState : "",
)
const syncUrl = computed(() => !!props.urlState && !props.skeleton)

function sortParam(sort: DataTableSortMeta[] | undefined): string {
  return (sort ?? [])
    .map((meta) => {
      const columnId = [...sortFunctions].find(([, f]) => f === meta.field)?.[0]
      return columnId ? `${meta.order == -1 ? "-" : ""}${columnId}` : null
    })
    .filter(Boolean)
    .join(",")
}

function urlParams(): QueryValues {
  const prefix = urlPrefix.value
  const sort = sortParam(multiSortMeta.value)
  const params: QueryValues = {
    [`${prefix}sort`]: sort == sortParam(defaultSortMeta()) ? null : sort,
  }
  const applied = getAppliedFilters()
  for (const column of props.columns) {
    if (column.filter?.enable) {
      params[`${prefix}f_${column.id}`] = applied[column.id] ?? null
    }
  }
  const page = Math.floor(first.value / rows.value) + 1
  params[`${prefix}page`] = page > 1 ? String(page) : null
  return params
}

function writeUrl() {
  if (!syncUrl.value) {
    return
  }
  const filterPrefix = `${urlPrefix.value}f_`
  // The filters of other columns, e.g. from an old link, are dropped
  replaceQuery(router, route, urlParams(), (key) =>
    key.startsWith(filterPrefix),
  )
}

/**
 * Set the state from the URL, which is user input: unknown, non-sortable or
 * non-filterable columns, orders, pages and select values are ignored.
 */
function readUrl() {
  if (!syncUrl.value) {
    return
  }
  const prefix = urlPrefix.value
  const query = route.query
  const sort = queryString(query, `${prefix}sort`)
  if (sort == undefined) {
    multiSortMeta.value = defaultSortMeta()
  } else {
    const metas = new Map<string, DataTableSortMeta>()
    for (const part of sort.split(",")) {
      const columnId = part.replace(/^-/, "")
      const column = props.columns.find((c) => c.id == columnId)
      if (column?.sortable && !metas.has(columnId)) {
        metas.set(columnId, {
          field: getSortFieldFunction(column),
          order: part.startsWith("-") ? -1 : 1,
        })
      }
    }
    multiSortMeta.value = [...metas.values()]
  }
  // Without filters shown, e.g. a small table, nothing to clear them
  if (useFilters.value) {
    const applied: Record<string, string> = {}
    for (const column of props.columns) {
      if (!column.filter?.enable) {
        continue
      }
      const text = queryString(query, `${prefix}f_${column.id}`)?.trim()
      const options = column.filter.options
      let model: string | null = options ? null : ""
      if (text && options) {
        model =
          options.find((o) => o.toLowerCase() == text.toLowerCase()) ?? null
      } else if (text) {
        model = text
      }
      filterModels[column.field].value = model
      if (model) {
        applied[column.id] = model.toLowerCase()
      }
    }
    appliedFilters.value = applied
    filtersKey = JSON.stringify(getAppliedFilters())
    applyFilters()
  }
  if (!useFilters.value) {
    applyFilters()
  }
  const page = Number(queryString(query, `${prefix}page`) ?? 1)
  first.value = clampFirst(
    Number.isInteger(page) && page > 1 ? (page - 1) * rows.value : 0,
  )
}

// A link to the same page with other params: the table isn't remounted
watch(
  () => route.query,
  () => {
    if (!syncUrl.value) {
      return
    }
    const params = urlParams()
    const changed = Object.entries(params).some(
      ([key, value]) => (queryString(route.query, key) ?? null) != value,
    )
    if (changed) {
      readUrl()
    }
  },
)

watch(multiSortMeta, writeUrl)
watch(first, writeUrl)

/**
 * Download the filtered data.
 * @param format
 */
async function download(format: "json" | "csv") {
  const fileName = props.exportTitle || "TSOSI_export"
  if (format == "csv") {
    exportCSV(props.columns, filteredData.value, fileName)
    return
  }
  exportJSON(props.columns, filteredData.value, fileName)
}

const exportItems = [
  {
    label: "Export CSV",
    icon: ["fas", "download"],
    command: () => download("csv"),
  },
  {
    label: "Export JSON",
    icon: ["fas", "download"],
    command: () => download("json"),
  },
]

/**
 * Toggle the button menu element when there are multiple buttons per row.
 * @param event
 * @param data
 */
function buttonMenuToggle(event: Event, data: Record<string, any>) {
  rowButtonMenu.value!.hide()
  if (
    selectedButtonData.value &&
    selectedButtonData.value[props.rowUniqueId] == data[props.rowUniqueId]
  ) {
    selectedButtonData.value = null
  } else {
    selectedButtonData.value = data
    nextTick(() => rowButtonMenu.value!.show(event))
  }
}

function buttonFromConfig(
  config: ButtonProps,
  data: Record<string, any>,
): ButtonProps {
  const buttonProps = {
    ...config,
  }
  buttonProps.data = data
  buttonProps.severity = "secondary"
  return buttonProps
}

/**
 * Scroll the document to the start of the table on page change.
 */
function onPageChange() {
  if (!tableComponent.value) {
    return
  }
  // @ts-expect-error PrimeVue component declartaion omits basic
  // VueJS attributes..
  tableComponent.value.$el.scrollIntoView({ behavior: "instant" })
}

/**
 * Populate the filters object for the DataTable component.
 * Filters not declared in this object are not displayed.
 */
function populateFilters() {
  if (!useFilters.value) {
    filters.value = undefined
    return
  }
  const newFilters: Record<string, any> = {}
  props.columns
    .filter((c) => c.filter != undefined)
    .forEach((c) => {
      newFilters[c.field] = {
        value: null,
        matchMode: FilterMatchMode.CONTAINS,
      }
      // A select filter without a value has no clear button
      filterModels[c.field] = ref(c.filter?.options ? null : "")
    })
  filters.value = newFilters
}

/**
 * Update the applied filters.
 * @param column
 * @param value
 */
async function filter(
  event: Event,
  column: TableColumnProps,
  value: string | null | undefined,
) {
  event.stopImmediatePropagation()
  if (!useFilters.value) {
    return
  }
  // console.log(`Column ${column.title} filter changed. Value: ${value}`)
  const currentFilters: { [id: string]: any } = {
    ...appliedFilters.value,
  }
  currentFilters[column.id] = value?.toLowerCase()
  appliedFilters.value = currentFilters
}

const debouncedFilter = debounce(filter, 200)

/**
 * Return the non-null applied filters.
 */
function getAppliedFilters(): AppliedFilters {
  return Object.keys(appliedFilters.value).reduce(
    (newObj: { [id: string]: string }, key) => {
      let value = appliedFilters.value[key]
      if (value !== null && value !== undefined) {
        value = value.replace(/\s+/g, " ").trim().toLowerCase() as string
        if (value !== "") {
          newObj[key] = value
        }
      }
      return newObj
    },
    {},
  )
}

/**
 * Filter the input dataset with the applied filters.
 */
function applyFilters() {
  const newData: Record<string, any>[] = []
  const filtersToApply = getAppliedFilters()
  if (Object.keys(filtersToApply).length > 0) {
    props.data.forEach((item) => {
      for (const columnId in filtersToApply) {
        const columnProps = props.columns.filter((c) => c.id == columnId)[0]
        const label = formatCellLabel(item, columnProps)
          ?.toString()
          .toLowerCase()
        const matches = columnProps.filter?.options
          ? label == filtersToApply[columnId]
          : label?.includes(filtersToApply[columnId])
        if (!matches) {
          return
        }
      }
      newData.push(item)
    })
    filteredData.value = newData
  } else {
    filteredData.value = props.data
  }
}

const hasAppliedFilters = computed(
  () => Object.keys(getAppliedFilters()).length > 0,
)

/**
 * The label of a cell as displayed in the table, also used for filtering.
 * Dates only show their year in tables, unless `fullDate`: the exports keep
 * the full date.
 * @param item
 * @param column
 */
function formatCellLabel(
  item: Record<string, any>,
  column: TableColumnProps,
): string | number | null {
  if (
    !column.fullDate &&
    (column.type == "dateWithPrecision" || column.type == "date")
  ) {
    const value = getItemLabel(item, column)
    const date = column.type == "dateWithPrecision" ? value?.value : value
    return date ? formatDateWithPrecision(date, "year") : ""
  }
  return formatItemLabel(item, column)
}

/**
 * Wether the given column is used for filtering.
 * @param column
 */
function isColumnFiltered(column: TableColumnProps): boolean {
  const filters = getAppliedFilters()
  return Object.keys(filters).includes(column.id)
}
</script>

<template>
  <DataTable
    class="tsosi-table"
    :value="filteredData"
    :frozenValue="props.frozenData?.length ? props.frozenData : undefined"
    ref="data-table"
    :paginator="props.data.length > 20 ? true : undefined"
    v-model:first="first"
    v-model:rows="rows"
    :rowsPerPageOptions="[10, 20, 50, 100]"
    v-model:multiSortMeta="multiSortMeta"
    :sortOrder="props.defaultSort?.sortOrder"
    sortMode="multiple"
    selectionMode="single"
    :dataKey="props.rowUniqueId"
    :rowClass="props.rowClass"
    :expandedRows="expandedRows"
    @page="onPageChange"
    :dt="{ row: { color: 'var(--color-text)' } }"
    :pt="{
      header: { style: props.header ? undefined : 'display: none' },
      footer: { style: hasAppliedFilters ? undefined : 'display: none' },
    }"
    v-model:filters="filters"
    :filterDisplay="filters ? 'row' : undefined"
    :tableStyle="
      props.fixedLayout
        ? `table-layout: fixed; min-width: ${props.fixedLayout.minWidth}`
        : undefined
    "
  >
    <!--
      The DataTable's slots are always given: a conditional slot would make
      Vue recreate them at each render, and remount the expanded row.
      The empty header and footer are hidden with `pt`.
    -->
    <template #header>
      <div v-if="props.header" class="table-header">
        <h2 class="table-title">
          {{ props.header.title }}
          <span v-if="!props.hideCount" class="table-count">
            {{ props.data.length.toLocaleString("fr-FR") }}
          </span>
        </h2>
        <div class="table-header__actions">
          <template v-if="!props.disableExport">
            <MenuButtonAtom
              :id="`table-export-menu-${props.id}`"
              :button="{
                id: `table-export-button-${props.id}`,
                label: 'Export',
                type: 'action',
                icon: ['fas', 'download'],
              }"
              :items="exportItems"
            />
          </template>
        </div>
      </div>
    </template>

    <template #footer>
      <div v-if="hasAppliedFilters" class="table-footer">
        Showing {{ filteredData.length }} out of {{ props.data.length }} items.
      </div>
    </template>
    <!-- Code to forward all of this component's slots to the DataTable slots
    <template v-for="(_, slot) of $slots" v-slot:[slot]="scope">
      <slot :name="slot" v-bind="scope" />
    </template>
    -->
    <Column
      v-for="column of displayedColumns"
      :field="column.field"
      :sortable="column.sortable ? true : undefined"
      :sortField="getSortFieldFunction(column)"
      :key="column.id"
      :pt="{
        pcColumnFilterButton: { style: 'display: none;' },
        pcColumnFilterClearButton: { style: 'display: none;' },
      }"
      :style="columnStyle(column)"
    >
      <!-- Header template -->
      <template #header>
        <span
          v-tooltip="{
            value: column.info,
            escape: false,
            autoHide: false,
          }"
        >
          <font-awesome-icon
            v-if="column.info"
            :icon="['fas', 'circle-question']"
          ></font-awesome-icon
        ></span>
        <span class="p-datatable-column-title">
          {{ column.title }}
        </span>
        <!-- Keep clicks and keys in the selector from sorting the column -->
        <span
          v-if="column.currencySelector"
          class="header-currency-selector"
          @click.stop
          @keydown.stop
        >
          <CurrencySelector showCode />
        </span>
      </template>

      <template v-if="useFilters && column.filter?.enable" #filter>
        <Select
          v-if="column.filter.options"
          v-model="filterModels[column.field].value"
          :options="column.filter.options"
          showClear
          class="table-filter"
          :class="{
            active: isColumnFiltered(column),
          }"
          :placeholder="column.filter.placeHolder || `All`"
          :style="`width: max(calc(${minWidthWithFilter} - 10px), 100%)`"
          @change="(event) => filter(event.originalEvent, column, event.value)"
        />
        <IconField v-else class="search-bar-input">
          <InputIcon class="filter-icon">
            <font-awesome-icon
              v-if="filterStatus == 'idle' || !isColumnFiltered(column)"
              :icon="['fas', 'magnifying-glass']"
            />
            <font-awesome-icon
              v-else
              :icon="['fas', 'spinner']"
              class="loader-icon-animate"
            />
          </InputIcon>
          <InputText
            v-model="filterModels[column.field].value"
            type="text"
            class="table-filter"
            @input="
              (event) =>
                debouncedFilter(event, column, filterModels[column.field].value)
            "
            :placeholder="column.filter.placeHolder || `Search ${column.title}`"
            :class="{
              active: isColumnFiltered(column),
            }"
            :style="`width: max(calc(${minWidthWithFilter} - 10px), 100%)`"
          />
        </IconField>
      </template>

      <!-- Row template -->
      <template v-if="props.skeleton" #body>
        <Skeleton></Skeleton>
      </template>
      <template v-else #body="{ data }">
        <div :class="props.cellClass?.(data, column)">
          <slot
            v-if="props.customCell?.(data, column)"
            name="cell"
            :data="data"
            :column="column"
          />
          <template v-else-if="column.type == 'entityLink'">
            <div class="inline-container">
              <div class="info-button-inline">
                <span
                  v-if="
                    column.field == 'emitter' &&
                    data.emitter?.is_child_transfer === true
                  "
                  v-tooltip.bottom="{
                    value:
                      'This contribution comes from a child entity, based on the ROR hierarchy. <a href=\'/pages/faq#entities-hierarchies\'>See our FAQ</a>.',
                    escape: false,
                    autoHide: false,
                    pt: { root: { class: 'left-aligned-tooltip' } },
                  }"
                >
                  <font-awesome-icon
                    :icon="['fas', 'circle-info']"
                  ></font-awesome-icon>
                </span>
              </div>
              <div
                class="entity-links-container"
                :class="[
                  { multiple: column.field == 'agents' },
                  column.highlightGetter?.(data)?.class,
                ]"
                v-tooltip.bottom="column.highlightGetter?.(data)?.tooltip"
              >
                <EntityLinkDataAtom
                  v-for="(entityData, index) of getEntityLinkRows(data, column)"
                  :key="`${column.id}-${entityData[column.field]?.id || entityData[column.field]?.name || index}`"
                  :data="entityData"
                  :dataField="column"
                  :hideIcon="column.field != 'recipient'"
                />
              </div>
              <span
                v-if="column.iconGetter?.(data)"
                class="cell-icon"
                v-tooltip.bottom="column.iconGetter(data)!.tooltip"
              >
                <font-awesome-icon :icon="column.iconGetter(data)!.icon" />
              </span>
            </div>
          </template>
          <template v-else-if="column.type == 'pageLink'">
            <RouterLink
              v-if="getItemLabel(data, column)"
              :to="getItemLink(data, column.fieldLink)"
            >
              {{ getItemLabel(data, column) }}
            </RouterLink>
          </template>
          <template v-else-if="column.type == 'externalLink'">
            <ExternalLinkAtom
              v-if="getItemLabel(data, column)"
              :href="getItemLink(data, column.fieldLink)"
              :label="getItemLabel(data, column)"
            />
          </template>
          <template v-else-if="column.type == 'country'">
            <Country
              :code="getItemLabel(data, column)"
              onlyFlag
              class="country-cell"
            />
          </template>
          <template v-else>
            <!-- The label has no space after it but before its suffix -->
            <div
              v-if="column.nullValueTemplate && !formatCellLabel(data, column)"
              v-html="column.nullValueTemplate"
            ></div>
            <template v-else-if="column.tagGetter">
              <span
                v-if="column.tagGetter(data)"
                v-tooltip.bottom="column.tagGetter(data)!.tooltip"
                class="cell-tag"
                tabindex="0"
                :aria-label="`${column.tagGetter(data)!.label}: ${column.tagGetter(data)!.tooltip}`"
              >
                {{ column.tagGetter(data)!.label }}
              </span>
            </template>
            <div v-else-if="column.linesGetter">
              <div
                v-for="(line, index) of column.linesGetter(data)"
                :key="index"
                class="cell-line"
              >
                {{ line.text }}
                <span v-if="line.detail" class="cell-line-detail">
                  {{ line.detail }}
                </span>
              </div>
            </div>
            <span v-else
              >{{ formatCellLabel(data, column)
              }}<span
                v-if="column.labelSuffix?.(data)"
                class="cell-label-suffix"
                >{{ ` ${column.labelSuffix(data)}` }}</span
              ></span
            >
            <span
              v-if="column.iconGetter?.(data)"
              class="cell-icon"
              v-tooltip.bottom="column.iconGetter(data)!.tooltip"
            >
              <font-awesome-icon :icon="column.iconGetter(data)!.icon" />
            </span>
          </template>
        </div>
      </template>
    </Column>

    <Column
      v-if="props.buttons || slots.actions"
      :style="
        props.fixedLayout?.actionsWidth
          ? `width: ${props.fixedLayout.actionsWidth}`
          : undefined
      "
    >
      <template #header>
        <div class="row-buttons header-buttons">
          <slot name="actionsHeader" />
        </div>
      </template>
      <template #body="{ data }">
        <div class="row-buttons">
          <slot name="actions" :data="data" />
          <template v-if="props.buttons && !props.hideButtons?.(data)">
            <!-- Menu with all buttons if more than 1 -->
            <Button
              v-if="props.buttons.length > 1"
              type="button"
              @click="buttonMenuToggle($event, data)"
              aria-haspopup="true"
              severity="secondary"
            >
              <font-awesome-icon :icon="['fas', 'ellipsis-vertical']" />
            </Button>
            <!-- Single button -->
            <CustomButton
              v-else
              v-bind="buttonFromConfig(props.buttons[0], data)"
            />
          </template>
        </div>
      </template>
    </Column>

    <template #expansion="{ data }">
      <slot name="expansion" :data="data" />
    </template>
  </DataTable>

  <Popover ref="row-button-menu">
    <div
      v-if="selectedButtonData"
      style="display: flex; flex-direction: column; gap: 0.5em"
    >
      <div v-for="button of props.buttons" :key="button.id">
        <CustomButton v-bind="buttonFromConfig(button, selectedButtonData)" />
      </div>
    </div>
  </Popover>

  <!--
    The export menu is located in the table's header when it's displayed
    otherwise at the bottom here
  -->
  <div class="table-export" v-if="!props.disableExport && !props.header">
    <h3 style="display: inline-block; margin-right: min(1em, 2vw)">
      Export data:
    </h3>
    <div style="display: inline-flex; gap: min(1em, 3vw); align-items: center">
      <MenuButtonAtom
        :id="`table-export-menu-${props.id}`"
        :button="{
          id: `table-export-button-${props.id}`,
          label: 'Export',
          type: 'action',
          icon: ['fas', 'download'],
        }"
        :items="exportItems"
      />
    </div>
    <div>
      <span>
        Data shared under a
        <RouterLink to="/pages/legal-notice">CC-BY-SA license</RouterLink>.
      </span>
    </div>
  </div>
</template>

<style scoped>
.tsosi-table {
  scroll-margin-top: calc(var(--regular-header-height) + 50px);
}

.table-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  row-gap: 1em;

  & h2 {
    font-weight: 900;
  }

  & .table-title {
    display: flex;
    flex-direction: row;
    gap: 1em;
    align-items: center;
  }
}

.table-header__actions {
  display: flex;
  gap: 0.5em;
}

.table-filter.active {
  border: 2px solid #e5a722;
}

.table-footer {
  text-align: center;
}

.cell-line + .cell-line {
  margin-top: 0.3em;
}

.cell-line-detail {
  white-space: nowrap;
  color: var(--p-neutral-500);
}

.cell-tag {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border: 1px solid var(--p-neutral-300);
  border-radius: 1rem;
  background: var(--p-neutral-50);
  font-size: 0.85rem;
  white-space: nowrap;
  cursor: help;
}

.cell-icon {
  margin-left: 0.4em;
  color: var(--p-neutral-500);
}

.inline-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: var(--p-datatable-header-cell-gap);
}

.header-currency-selector {
  margin-left: 0.5em;
}

.cell-label-suffix {
  color: var(--p-neutral-500);
}

.info-button-inline {
  color: var(--p-neutral-500);
}

.entity-links-container {
  display: flex;
}

.row-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.3rem;
}

.header-buttons {
  width: 100%;
}

.country-cell {
  justify-content: center;
}

.entity-links-container.multiple {
  gap: 0.2em;
}
</style>
