<script setup lang="ts">
import {
  ref,
  watch,
  computed,
  type Ref,
  nextTick,
  useTemplateRef,
  onBeforeMount,
} from "vue"
import { RouterLink } from "vue-router"
import DataTable from "primevue/datatable"
import { FilterMatchMode } from "@primevue/core/api"
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Column from "primevue/column"
import Skeleton from "primevue/skeleton"
import Button from "primevue/button"
import Popover from "primevue/popover"
import {
  formatItemLabel,
  type DataFieldProps,
  resolveValueFromPath,
  getItemLabel,
  getItemLink,
  getCountryLabel,
  exportCSV,
  exportJSON,
} from "@/utils/data-utils"
import debounce, { type DebounceStatus } from "@/utils/debounce"
import CurrencySelector from "@/components/CurrencySelector.vue"
import CustomButton, {
  type ButtonProps,
} from "@/components/atoms/ButtonAtom.vue"
import Country from "@/components/atoms/CountryAtom.vue"
import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"
import MenuButtonAtom from "@/components/atoms/MenuButtonAtom.vue"
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import EntityLinkDataAtom from "@/components/atoms/EntityLinkDataAtom.vue"
interface AppliedFilters {
  [columnId: string]: string
}

export interface TableColumnProps extends DataFieldProps {
  sortable?: boolean
  sortField?: string // field used to sort the column. Defaults to fieldLabel
  info?: string
  infoLink?: {
    href: string
    label: string
    type: "internal" | "external"
  }
  currencySelector?: boolean
  nullValueTemplate?: string
  filter?: {
    enable?: boolean
    placeHolder?: string
  }
}

export interface TableProps {
  id: string
  data: Array<Record<string, any>>
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
  storeState?: boolean
  rowSelectable?: boolean
  buttons?: Array<ButtonProps>
  disableExport?: boolean
  exportTitle?: string
  hideCount?: boolean
}

const props = defineProps<TableProps>()
// Holds the declared filters for the DataTable component
// We handle filtering manually. The important thing is to use our custom
// ref `filterModels` to avoid the component built-in filtering.
const filters: Ref<
  { [id: string]: { value: any; matchMode: "" } } | undefined
> = ref({})
const filterModels: { [id: string]: Ref<string | null | undefined> } = {}
const minDataForFilters = 10
// Holds the applied filters in the form { columnId: filterValue }
const appliedFilters: Ref<AppliedFilters> = ref({})
const filteredData: Ref<Array<Record<string, any>>> = ref([])
const minWidthWithFilter = "100px"
const useFilters = computed(
  () => !props.skeleton && props.data.length >= minDataForFilters,
)
const filterStatus: Ref<DebounceStatus> = ref("idle")

onBeforeMount(() => {
  // Prepare filters
  populateFilters()
  applyFilters()
})

watch(appliedFilters, debounce(applyFilters, 250, filterStatus))

const tableComponent = useTemplateRef("data-table")
const rowButtonMenu = useTemplateRef("row-button-menu")
const selectedButtonData: Ref<Record<string, any> | null> = ref(null)

function getSortFieldFunction(columnProps: TableColumnProps) {
  if (!columnProps.sortable) {
    return undefined
  }
  return (item: Record<string, any>) => getSortValue(item, columnProps)
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
  }
  return getItemLabel(item, columnProps)
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
      filterModels[c.field] = ref("")
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
      const value = appliedFilters.value[key]
      if (!["", null, undefined].includes(value)) {
        newObj[key] = value
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
        if (
          !formatItemLabel(item, columnProps)
            ?.toString()
            .toLowerCase()
            .includes(filtersToApply[columnId])
        ) {
          return
        }
      }
      newData.push(item)
    })
    filteredData.value = newData
  } else {
    filteredData.value = props.data
  }
  console.log("Dataset Filtered!")
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
    ref="data-table"
    :paginator="props.data.length > 20 ? true : undefined"
    :rows="20"
    :rowsPerPageOptions="[10, 20, 50, 100]"
    :multi-sort-meta="
      props.defaultSort
        ? [
            {
              field: defaultSortFieldFunction(),
              order: props.defaultSort.sortOrder,
            },
          ]
        : undefined
    "
    :sortOrder="props.defaultSort?.sortOrder"
    sortMode="multiple"
    selectionMode="single"
    :dataKey="props.rowUniqueId"
    @page="onPageChange"
    :dt="{ row: { color: 'var(--color-text)' } }"
    v-model:filters="filters"
    :filterDisplay="filters ? 'row' : undefined"
  >
    <template v-if="props.header" #header>
      <div class="table-header">
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

    <template #footer v-if="Object.keys(getAppliedFilters()).length > 0">
      <div class="table-footer">
        Showing {{ filteredData.length }} out of {{ props.data.length }} items.
      </div>
    </template>
    <!-- Code to forward all of this component's slots to the DataTable slots
    <template v-for="(_, slot) of $slots" v-slot:[slot]="scope">
      <slot :name="slot" v-bind="scope" />
    </template>
    -->
    <Column
      v-for="column of columns"
      :field="column.field"
      :sortable="column.sortable ? true : undefined"
      :sortField="getSortFieldFunction(column)"
      :key="column.id"
      :pt="{
        pcColumnFilterButton: { style: 'display: none;' },
        pcColumnFilterClearButton: { style: 'display: none;' },
      }"
      :style="
        column.filter?.enable ? `min-width: ${minWidthWithFilter}` : undefined
      "
    >
      <!-- Header template -->
      <template #header>
        <InfoButtonAtom v-if="column.info || column.infoLink">
          <template #popup>
            <span v-if="column.info"> {{ column.info }}&nbsp; </span>
            <RouterLink
              v-if="column.infoLink?.type == 'internal'"
              :to="column.infoLink.href"
            >
              {{ column.infoLink.label }}
            </RouterLink>
            <ExternalLinkAtom
              v-else-if="column.infoLink?.type == 'external'"
              :href="column.infoLink.href"
            >
              {{ column.infoLink.label }}
            </ExternalLinkAtom>
          </template>
        </InfoButtonAtom>
        <span class="p-datatable-column-title">
          {{ column.title }}
        </span>
        <CurrencySelector v-if="column.currencySelector" />
      </template>

      <template v-if="useFilters && column.filter?.enable" #filter>
        <IconField class="search-bar-input">
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
      <template v-else-if="column.type == 'entityLink'" #body="{ data }">
        <EntityLinkDataAtom :data="data" :dataField="column" />
      </template>
      <template v-else-if="column.type == 'pageLink'" #body="{ data }">
        <RouterLink
          v-if="getItemLabel(data, column)"
          :to="getItemLink(data, column.fieldLink)"
        >
          {{ getItemLabel(data, column) }}
        </RouterLink>
      </template>
      <template v-else-if="column.type == 'externalLink'" #body="{ data }">
        <ExternalLinkAtom
          v-if="getItemLabel(data, column)"
          :href="getItemLink(data, column.fieldLink)"
          :label="getItemLabel(data, column)"
        />
      </template>
      <template v-else-if="column.type == 'country'" #body="{ data }">
        <Country :code="getItemLabel(data, column)" />
      </template>
      <template v-else #body="{ data }">
        <div
          v-if="column.nullValueTemplate && !formatItemLabel(data, column)"
          v-html="column.nullValueTemplate"
        ></div>
        <span v-else>
          {{ formatItemLabel(data, column) }}
        </span>
      </template>
    </Column>

    <Column v-if="props.buttons">
      <!-- Menu with all buttons if more than 1 -->
      <template #body="{ data }" v-if="props.buttons.length > 1">
        <Button
          type="button"
          @click="buttonMenuToggle($event, data)"
          aria-haspopup="true"
          severity="secondary"
        >
          <font-awesome-icon :icon="['fas', 'ellipsis-vertical']" />
        </Button>
      </template>
      <!-- Single button -->
      <template #body="{ data }" v-else>
        <CustomButton v-bind="buttonFromConfig(props.buttons[0], data)" />
      </template>
    </Column>
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
        <RouterLink to="/pages/legal-notice/">CC-BY-SA license</RouterLink>.
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
</style>
