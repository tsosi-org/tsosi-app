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
const transfers: Ref<Transfer[] | null> = ref(null)
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
  updatedTransfers.forEach((t) =>
    fillTransferAmountCurrency(
      t,
      selectedCurrency.value.id,
      amountColumn,
      currencyColumn,
    ),
  )
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

  const cleanedTransfers:Transfer[] = []
  for (const transfer of rawTransfers) {
    fillTransferAmountCurrency(
      transfer,
      selectedCurrency.value.id,
      amountColumn,
      currencyColumn,
    )
    if (props.entity.children.some((c) => c == transfer.emitter_id)) {
      transfer.emitter = {
        ...transfer.emitter,
        is_child_transfer: true,
      }
    }
    cleanedTransfers.push(transfer)
  }
  transfers.value = cleanedTransfers
}

const currencyColumn = "__currency"
const amountColumn = "__amount"
const baseColumns: TableColumnProps[] = [
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

const exportString = `TSOSI_${props.entity.name.replace(/\s+/g, "_")}`
// Config for the transfer table
const tableProps = computed(() => {
  if (!transfers.value?.length) {
    return null
  }
  let toRemoveCols: string[] = []
  if (transfers.value.every((t) => t.amount == null)) {
    toRemoveCols.push("currency")
    if (props.entity.is_recipient) {
      toRemoveCols.push("amount")
    }
  }
  if (transfers.value.every((t) => t.agent == null)) {
    toRemoveCols.push("agent")
  }
  if (transfers.value.every((t) => t.emitter_id == props.entity.id)) {
    toRemoveCols.push("emitter")
  }
  if (!props.entity.is_recipient) {
    toRemoveCols.push("emitterCountry")
  }
  if (transfers.value.every((t) => t.recipient_id == props.entity.id)) {
    toRemoveCols.push("recipient")
  }

  return {
    id: `${props.entity.id}-transfers`,
    data: transfers.value,
    columns: baseColumns.filter((col) => !toRemoveCols.includes(col.id)),
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
  columns: baseColumns,
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
  <div v-if="props.entity.is_recipient && props.entity.is_partner">
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
              v-if="tableProps"
              v-bind="tableProps"
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
      <Table v-if="tableProps" v-bind="tableProps"></Table>
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
