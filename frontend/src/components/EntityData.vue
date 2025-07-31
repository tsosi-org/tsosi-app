<script setup lang="ts">
import Tab from "primevue/tab"
import TabList from "primevue/tablist"
import TabPanel from "primevue/tabpanel"
import TabPanels from "primevue/tabpanels"
import Tabs from "primevue/tabs"
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  useTemplateRef,
  watch,
  type Ref,
  type ShallowRef,
} from "vue"

import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import EntityHistogram from "@/components/EntityHistogram.vue"
import EntityMap from "@/components/EntityMap.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { selectedCurrency } from "@/singletons/currencyStore"
import {
  getEmittersForEntity,
  getTransfers,
  type Entity,
  type EntityDetails,
  type Transfer,
  type TransferEntityType,
} from "@/singletons/ref-data"
import { fillTransferAmountCurrency } from "@/utils/data-utils"
import { getTransferBaseUrl } from "@/utils/url-utils"


const props = defineProps<{
  entity: EntityDetails
}>()

const noHistogramIds =
  import.meta.env.VITE_INFRA_HISTOGRAM_OPT_OUT?.split(",") || []
// Whether to display the histogram
const displayHistogram = computed(() => {
  if (!noHistogramIds.length) {
    return true
  }
  return !props.entity.identifiers.some((id) =>
    noHistogramIds.includes(id.value),
  )
})

// Refs for test.
// There seems to be Memory leak because of the datatable component,
// mainly caused by this skeleton table.
const displaySkeletonTable = ref(true)

// Transfer data
const transfers: Ref<Record<TransferEntityType, Transfer[]> | null> = ref(null)
// Stores whether there's at least 1 transfer with a discoled amount
const showAmount: Ref<boolean> = ref(true)
// Tabs
const activeTab = ref("0")
const tabs = useTemplateRef("entity-tabs")
// This ref is used to trigger chart data fetching only when the tab is
// selected
const chartTabTriggered = ref(false)
const emittersData: ShallowRef<Entity[]> = shallowRef([])
const mapDataLoaded = ref(false)

onMounted(async () => {
  await updateTransfers()
})

onBeforeUnmount(() => {
  transfers.value = null
})

watch(selectedCurrency, () => {
  if (!transfers.value) {
    return
  }
  const updatedTransfers = transfers.value
  for (const key in updatedTransfers) {
    updatedTransfers[key as TransferEntityType].forEach((t) =>
      fillTransferAmountCurrency(
        t,
        selectedCurrency.value.id,
        amountColumn,
        currencyColumn,
      ),
    )
  }
})
watch(activeTab, () => {
  if (activeTab.value == "1" && chartTabTriggered.value !== true) {
    chartTabTriggered.value = true
  }
})
watch(chartTabTriggered, () => {
  if (chartTabTriggered.value === true) {
    // Scroll the tab panel back to top for the first
    if (tabs.value != null) {
      // @ts-expect-error PrimeVue component declaration omits basic
      // VueJS attributes..
      const tabPanelEl: HTMLElement = tabs.value.$el
      if (tabPanelEl.getBoundingClientRect().top < 0) {
        tabPanelEl.scrollIntoView({ behavior: "instant" })
      }
    }
    updateMapData()
  }
})

async function updateTransfers() {
  const rawTransfers = await getTransfers(props.entity.id)
  if (!rawTransfers) {
    return
  }

  const sortedTransfers: { [key in TransferEntityType]: Transfer[] } = {
    emitter: [],
    recipient: [],
    agent: [],
  }
  let transferWithAmount = false
  for (const transfer of rawTransfers) {
    fillTransferAmountCurrency(
      transfer,
      selectedCurrency.value.id,
      amountColumn,
      currencyColumn,
    )
    if (transfer.amount) {
      transferWithAmount = true
    }
    if (transfer.emitter_id == props.entity.id) {
      sortedTransfers["emitter"].push(transfer)
    } else if (transfer.recipient_id == props.entity.id) {
      sortedTransfers["recipient"].push(transfer)
    } else if (transfer.agent_id == props.entity.id) {
      sortedTransfers["agent"].push(transfer)
    } else {
      console.warn(
        `Following transfer does not involve entity ${props.entity.id}: ${transfer}`,
      )
    }
  }
  showAmount.value = transferWithAmount
  transfers.value = sortedTransfers
}

const currencyColumn = "__currency"
const amountColumn = "__amount"
const baseSupporterColumns: TableColumnProps[] = [
  {
    id: "date_clc",
    title: "Date",
    field: "date_clc",
    type: "dateWithPrecision",
    sortable: true,
    info: "The date field is relative.",
    infoLink: {
      href: "/pages/faq#what-does-the-date-column-refer-to",
      label: "See more in FAQ",
      type: "internal",
    },
    filter: {
      enable: true,
    },
  },
  {
    id: "emitter",
    title: "Supporter",
    field: "emitter",
    type: "entityLink",
    fieldLabel: "emitter.name",
    sortable: true,
    filter: {
      enable: true,
    },
  },
  {
    id: "agent",
    title: "Intermediary",
    field: "agent",
    type: "entityLink",
    fieldLabel: "agent.name",
    sortable: true,
    info: "When a transfer is done through another entity like a library consortia, it appears in this column.",
    filter: {
      enable: true,
    },
  },
  {
    id: "recipient",
    title: "Beneficiary",
    field: "recipient",
    type: "entityLink",
    fieldLabel: "recipient.short_name", // This is only used for filtering - All recipients have shortnames so it works fine for now
    sortable: true,
    filter: {
      enable: true,
    },
  },
  {
    id: "amount",
    title: "Amount",
    field: amountColumn,
    type: "number",
    sortable: true,
    nullValueTemplate: '<span class="data-label hidden-amount">hidden</span>',
  },
  {
    id: "currency",
    title: "Currency",
    field: currencyColumn,
    type: "string",
    currencySelector: true,
  },
]

const baseInfrastructureColumns: TableColumnProps[] = [
  {
    id: "date_clc",
    title: "Date",
    field: "date_clc",
    type: "dateWithPrecision",
    sortable: true,
    info: "The date field is relative.",
    infoLink: {
      href: "/pages/faq#what-does-the-date-column-refer-to",
      label: "See more in FAQ",
      type: "internal",
    },
    filter: {
      enable: true,
    },
  },
  {
    id: "emitter",
    title: "Supporter",
    field: "emitter",
    type: "entityLink",
    fieldLabel: "emitter.name",
    sortable: true,
    filter: {
      enable: true,
    },
  },
  {
    id: "emitterCountry",
    title: "Country",
    field: "emitter.country",
    type: "country",
    sortable: true,
    filter: {
      enable: true,
    },
  },
  {
    id: "agent",
    title: "Intermediary",
    field: "agent",
    type: "entityLink",
    fieldLabel: "agent.name",
    sortable: true,
    info: "When a transfer is done through another entity like a library consortia, it appears in this column.",
    filter: {
      enable: true,
    },
  },
  {
    id: "amount",
    title: "Amount",
    field: amountColumn,
    type: "number",
    sortable: true,
    nullValueTemplate: '<span class="data-label hidden-amount">hidden</span>',
  },
  {
    id: "currency",
    title: "Currency",
    field: currencyColumn,
    type: "string",
    currencySelector: true,
  },
]

/**
 * Adapt the transfer table columns according to parameters and the data to
 * display.
 * @param showAmount
 * @param removedColumns
 */
function getTableColumns(
  baseColumns: TableColumnProps[],
  showAmount: boolean,
  transfers: Transfer[],
  removedColumns: string[] = [],
): TableColumnProps[] {
  let columns = baseColumns.filter((col) => !removedColumns.includes(col.id))
  if (!showAmount) {
    const toRemove = props.entity.infrastructure
      ? ["amount", "currency"]
      : ["currency"]
    columns = columns.filter((col) => !toRemove.includes(col.id))
  }
  if (transfers.every((t) => t.agent == null)) {
    columns = columns.filter((col) => col.id != "agent")
  }
  return columns
}

const buttons: Array<ButtonProps> = [
  {
    id: "transferDetails",
    icon: ["fas", "magnifying-glass"],
    type: "pageLink",
    linkConfig: {
      base: getTransferBaseUrl(),
      suffix: "id",
      suffixType: "field",
    },
  },
]

// Config for the supporter transfer table
const exportString = `TSOSI_${props.entity.name.replace(/\s+/g, "_")}`
const supporterTableProps = computed(() => {
  if (!transfers.value?.emitter.length && !transfers.value?.agent.length) {
    return null
  }
  const toRemoveCols = []
  const supporterData = [...transfers.value.emitter, ...transfers.value.agent]
  // If there are no transfers as an agent, remove the emitterCountry column to
  // lighten the layout
  if (!transfers.value.agent?.length) {
    toRemoveCols.push("emitterCountry")
    toRemoveCols.push("emitter")
  }
  return {
    id: `${props.entity.id}-emitter`,
    data: supporterData,
    columns: getTableColumns(
      baseSupporterColumns,
      showAmount.value,
      supporterData,
      toRemoveCols,
    ),
    defaultSort: {
      sortField: "date_clc",
      sortOrder: -1 as 0 | 1 | -1,
    },
    rowUniqueId: "id",
    buttons: buttons,
    exportTitle: exportString,
  }
})

// Config for the infrastructure transfer table
const recipientTableProps = computed(() => {
  if (!transfers.value?.recipient.length) {
    return null
  }
  return {
    id: `${props.entity.id}-recipient`,
    data: transfers.value.recipient,
    columns: getTableColumns(
      baseInfrastructureColumns,
      showAmount.value,
      transfers.value.recipient,
      ["recipient"],
    ),
    defaultSort: {
      sortField: "date_clc",
      sortOrder: -1 as 0 | 1 | -1,
    },
    rowUniqueId: "id",
    buttons: buttons,
    exportTitle: exportString,
  }
})

const skeletonTableProps = {
  id: `${props.entity.id}-skeleton-table`,
  data: new Array(10).fill({ field: "dummy" }),
  columns: props.entity.is_recipient
    ? baseInfrastructureColumns
    : baseSupporterColumns,
  rowUniqueId: "id",
  skeleton: true,
  exportTitle: exportString,
  hideCount: true,
  disableExport: true,
}

async function updateMapData() {
  const emitters = await getEmittersForEntity(props.entity.id)
  if (emitters != null) {
    emittersData.value = emitters
  }
  mapDataLoaded.value = true
}
</script>

<template>
  <div v-if="props.entity.is_recipient">
    <Tabs v-model:value="activeTab" ref="entity-tabs">
      <TabList class="tab-list">
        <Tab value="0" as="button">
          <span class="tab-header">
            <font-awesome-icon class="icon" :icon="['fas', 'list-ul']" />
            <span>Table</span>
          </span>
        </Tab>
        <Tab value="1" as="button">
          <span class="tab-header">
            <font-awesome-icon class="icon" :icon="['fas', 'chart-column']" />
            <span>Charts</span>
          </span>
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="0">
          <div v-if="!transfers && displaySkeletonTable">
            <!-- @vue-ignore -->
            <Table v-bind="skeletonTableProps"></Table>
          </div>
          <div v-if="transfers" class="transfer-tables">
            <Table
              v-if="recipientTableProps"
              v-bind="recipientTableProps"
            ></Table>
            <Table
              v-if="supporterTableProps"
              v-bind="supporterTableProps"
            ></Table>
          </div>
        </TabPanel>
        <TabPanel value="1">
          <div class="data-chart-panel">
            <div v-if="chartTabTriggered" class="dataviz-wrapper">
              <EntityMap
                :id="`entity-map-${props.entity.id}`"
                :supporters="emittersData"
                :title="'Location of the supporters'"
                :data-loaded="mapDataLoaded"
                :export-title-base="props.entity.name"
                :show-legend="true"
              />
            </div>
            <div
              v-if="displayHistogram && chartTabTriggered"
              class="dataviz-wrapper"
            >
              <EntityHistogram :entity="props.entity" class="entity-chart" />
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
  <div v-else>
    <div v-if="!transfers && displaySkeletonTable">
      <!-- @vue-ignore -->
      <Table v-bind="skeletonTableProps"></Table>
    </div>
    <div v-if="transfers" class="transfer-tables">
      <Table v-if="recipientTableProps" v-bind="recipientTableProps"></Table>
      <Table v-if="supporterTableProps" v-bind="supporterTableProps"></Table>
    </div>
  </div>
</template>

<style scoped>
.tab-list {
  position: sticky;
  top: var(--header-height);
  z-index: 2000;
}

.tab-header {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  gap: 0.6em;
  align-items: center;
  font-size: 1.3em;
}

.transfer-tables > * {
  margin-bottom: 2em;
}

.transfer-tables > *:last-child {
  margin-bottom: initial;
}

.data-chart-panel {
  width: 100%;
  padding: 1em 0;

  & > * {
    margin-bottom: 4rem;
  }
}

.dataviz-wrapper {
  width: 100%;
  overflow-x: auto;
}
</style>
