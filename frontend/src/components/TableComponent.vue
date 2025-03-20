<script setup lang="ts">
import { ref, type Ref, nextTick, useTemplateRef } from "vue"
import { RouterLink } from "vue-router"
import DataTable from "primevue/datatable"
import Menu from "primevue/menu"
import Column from "primevue/column"
import Skeleton from "primevue/skeleton"
import Button from "primevue/button"
import Popover from "primevue/popover"
import {
  formatItemLabel,
  type DateWithPrecision,
  type DataFieldProps,
  resolveValueFromPath,
  getItemLabel,
  getItemLink,
  getCountryLabel,
  exportCSV,
  exportJSON,
} from "@/utils/data-utils"
import CurrencySelector from "./CurrencySelector.vue"
import CustomButton, {
  type ButtonProps,
} from "@/components/atoms/ButtonAtom.vue"
import Country from "@/components/atoms/CountryAtom.vue"
import InfoButtonAtom from "./atoms/InfoButtonAtom.vue"

export interface TableColumnProps extends DataFieldProps {
  sortable?: boolean
  sortField?: string // field used to sort the column. Defaults to fieldLabel
  info?: string
}

export interface TableProps {
  id: string
  data: Array<Record<string, any>>
  columns: Array<TableColumnProps>
  header?: {
    title: string
  }
  defaultSort?: {
    sortField: string
    sortOrder: number
  }
  rowUniqueId: string
  skeleton?: boolean
  storeState?: boolean
  currencySelector?: boolean
  rowSelectable?: boolean
  buttons?: Array<ButtonProps>
  disableExport?: boolean
  exportTitle?: string
  hideCount?: boolean
}

const props = defineProps<TableProps>()

const tableComponent = useTemplateRef("data-table")
const exportMenu = useTemplateRef("export-menu")
const rowButtonMenu = useTemplateRef("row-button-menu")
const selectedButtonData: Ref<Record<string, any> | null> = ref(null)

function getSortFieldFunction(columnProps: TableColumnProps) {
  if (!columnProps.sortable) {
    return undefined
  }
  if (columnProps.type == "country") {
    return (item: Record<string, any>) => {
      const country = getItemLabel(item, columnProps)
      return country ? getCountryLabel(country) : null
    }
  } else if (columnProps.type == "dateWithPrecision") {
    return (item: Record<string, any>) =>
      getDateWithPrecisionValue(item, columnProps)
  }
  return (item: Record<string, any>) => getSortValue(item, columnProps)
}

function getSortValue(
  item: Record<string, any>,
  columnProps: TableColumnProps,
): any {
  if (columnProps.sortField) {
    return resolveValueFromPath(item, columnProps.sortField)
  }
  if (columnProps.type) return getItemLabel(item, columnProps)
}

function getDateWithPrecisionValue(
  item: Record<string, any>,
  columnProps: TableColumnProps,
): Date | undefined {
  const date: DateWithPrecision | null = resolveValueFromPath(
    item,
    columnProps.field,
  )
  return date?.dateObj
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

async function download(format: "json" | "csv") {
  const fileName = props.exportTitle || "TSOSI_export"
  if (format == "csv") {
    exportCSV(props.columns, props.data, fileName)
    return
  }
  exportJSON(props.columns, props.data, fileName)
}

const exportItems = ref([
  {
    label: "Export CSV",
    icon: "download",
    command: () => download("csv"),
  },
  {
    label: "Export JSON",
    icon: "download",
    command: () => download("json"),
  },
])

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

function toggleExportMenu(event: Event) {
  exportMenu.value!.toggle(event)
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
  tableComponent.value.$el.scrollIntoView()
}
</script>

<template>
  <!-- Params to store table state in local storage.
    :stateStorage="props.storeState ? 'local' : undefined" :stateKey="`tsosi-table-${props.id}`"
  -->
  <DataTable
    class="tsosi-table"
    :value="props.data"
    ref="data-table"
    :paginator="props.data.length > 20 ? true : undefined"
    :rows="20"
    :rowsPerPageOptions="[10, 20, 50, 100]"
    :sortField="defaultSortFieldFunction()"
    :sortOrder="props.defaultSort?.sortOrder"
    selectionMode="single"
    :dataKey="props.rowUniqueId"
    @page="onPageChange"
    :dt="{ row: { color: 'var(--color-text)' } }"
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
          <CurrencySelector v-if="props.currencySelector" />
          <template v-if="!props.disableExport">
            <Button
              label="Export"
              type="button"
              @click="toggleExportMenu"
              aria-haspopup="true"
              :aria-controls="`table-export-menu-${props.id}`"
            >
              <template #icon>
                <font-awesome-icon icon="download" />
              </template>
            </Button>
            <Menu
              ref="export-menu"
              :id="`table-export-menu-${props.id}`"
              :model="exportItems"
              :popup="true"
            >
              <template #itemicon="{ item }">
                <font-awesome-icon :icon="item.icon" />
              </template>
            </Menu>
          </template>
        </div>
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
      :header="column.title"
      :sortable="column.sortable ? true : undefined"
      :sortField="getSortFieldFunction(column)"
      :key="column.id"
    >
      <!-- Header template -->
      <template v-if="column.info" #header>
        <InfoButtonAtom :content="column.info" />
      </template>

      <!-- Row template -->
      <template v-if="props.skeleton" #body>
        <Skeleton></Skeleton>
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
        <a
          v-if="getItemLabel(data, column)"
          :href="getItemLink(data, column.fieldLink)"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ getItemLabel(data, column) }}
        </a>
      </template>
      <template v-else-if="column.type == 'country'" #body="{ data }">
        <Country :code="getItemLabel(data, column)" />
      </template>
      <template v-else #body="{ data }">
        {{ formatItemLabel(data, column) }}
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
          <font-awesome-icon icon="ellipsis-vertical" />
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
</template>

<style scoped>
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
</style>
