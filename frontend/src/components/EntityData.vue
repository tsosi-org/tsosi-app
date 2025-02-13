<script setup lang="ts">
import {
  getTransferts,
  type EntityDetails,
  type DeepReadonly,
  type Transfert,
  type TransfertEntityType,
} from "@/singletons/ref-data"
import { ref, type Ref, onMounted, watch, computed } from "vue"
import EntityHistogram from "@/components/EntityHistogram.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { getEntityBaseUrl, getTransfertBaseUrl } from "@/utils/url-utils"
import { selectedCurrency } from "@/singletons/currencyStore"
import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import { fillTransfertAmountCurrency } from "@/utils/data-utils"
import Tabs from "primevue/tabs"
import TabList from "primevue/tablist"
import Tab from "primevue/tab"
import TabPanels from "primevue/tabpanels"
import TabPanel from "primevue/tabpanel"

const props = defineProps<{
  entity: DeepReadonly<EntityDetails>
}>()

const transferts: Ref<Record<TransfertEntityType, Transfert[]> | null> =
  ref(null)
const showAmount: Ref<boolean> = ref(true)
// Tabs
const activeTab = ref("0")
// This ref is used to trigger chart data fetching only when the tab is
// selected
const chartTabTriggered = ref(false)

onMounted(async () => {
  update_transferts()
})

watch(selectedCurrency, () => {
  if (!transferts.value) {
    return
  }
  const updatedTransferts = transferts.value
  for (const key in updatedTransferts) {
    updatedTransferts[key as TransfertEntityType].forEach((t) =>
      fillTransfertAmountCurrency(
        t,
        selectedCurrency.value.id,
        amountColumn,
        currencyColumn,
      ),
    )
  }
})
watch(activeTab, () => {
  if (activeTab.value == "1") {
    chartTabTriggered.value = true
  }
})

async function update_transferts() {
  const rawTransferts = await getTransferts(props.entity.id)
  if (!rawTransferts) {
    return
  }

  const sortedTransferts: { [key in TransfertEntityType]: Transfert[] } = {
    emitter: [],
    recipient: [],
    agent: [],
  }
  let transfertWithAmount = false
  for (const transfert of rawTransferts) {
    fillTransfertAmountCurrency(
      transfert,
      selectedCurrency.value.id,
      amountColumn,
      currencyColumn,
    )
    if (transfert.amount) {
      transfertWithAmount = true
    }
    if (transfert.emitter_id == props.entity.id) {
      sortedTransferts["emitter"].push(transfert)
    } else if (transfert.recipient_id == props.entity.id) {
      sortedTransferts["recipient"].push(transfert)
    } else if (transfert.agent_id == props.entity.id) {
      sortedTransferts["agent"].push(transfert)
    } else {
      console.warn(
        `Following transfert does not involve entity ${props.entity.id}: ${transfert}`,
      )
    }
  }
  showAmount.value = transfertWithAmount
  transferts.value = sortedTransferts
}

const currencyColumn = "__currency"
const amountColumn = "__amount"
const baseTableColumns: TableColumnProps[] = [
  {
    id: "date_clc",
    title: "Date",
    field: "date_clc",
    type: "dateWithPrecision",
    sortable: true,
  },
  {
    id: "emitter",
    title: "Supporter",
    field: "emitter",
    type: "pageLink",
    fieldLabel: "emitter.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "emitter.id",
      suffixType: "field",
    },
    sortable: true,
  },
  {
    id: "emitterCountry",
    title: "Country",
    field: "emitter.country",
    type: "country",
    sortable: true,
  },
  {
    id: "recipient",
    title: "Beneficiary",
    field: "recipient",
    type: "pageLink",
    fieldLabel: "recipient.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "recipient.id",
      suffixType: "field",
    },
    sortable: true,
  },
  {
    id: "agent",
    title: "Agent",
    field: "agent",
    type: "pageLink",
    fieldLabel: "agent.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "agent.id",
      suffixType: "field",
    },
    sortable: true,
  },
  {
    id: "amount",
    title: "Amount",
    field: amountColumn,
    type: "number",
    sortable: true,
  },
  {
    id: "currency",
    title: "Currency",
    field: currencyColumn,
    type: "string",
  },
]

/**
 * Adapt the transfert table columns according to parameters and the data to
 * display.
 * @param showAmount
 * @param removedColumns
 */
function getTableColumns(
  showAmount: boolean,
  transferts: Transfert[],
  removedColumns: string[] = [],
): TableColumnProps[] {
  let columns = baseTableColumns.filter(
    (col) => !removedColumns.includes(col.id),
  )
  if (!showAmount) {
    columns = columns.filter((col) => !["amount", "currency"].includes(col.id))
  }
  if (transferts.every((t) => t.agent == null)) {
    columns = columns.filter((col) => col.id != "agent")
  }
  return columns
}

const buttons: Array<ButtonProps> = [
  {
    id: "transfertDetails",
    icon: "magnifying-glass",
    type: "pageLink",
    linkConfig: {
      base: getTransfertBaseUrl(),
      suffix: "id",
      suffixType: "field",
    },
  },
]

const exportString = `TSOSI_${props.entity.name.replace(/\s+/g, "_")}`
const emitterTableProps = computed(() => {
  if (!transferts.value?.emitter.length) {
    return null
  }
  return {
    id: `${props.entity.id}-emitter`,
    data: transferts.value.emitter,
    columns: getTableColumns(showAmount.value, transferts.value.emitter, [
      "emitter",
      "emitterCountry",
    ]),
    defaultSort: {
      sortField: "date_clc",
      sortOrder: -1,
    },
    header: {
      title: "Transferts emitted",
    },
    rowUniqueId: "id",
    currencySelector: showAmount.value,
    buttons: buttons,
    exportTitle: exportString,
  }
})

const recipientTableProps = computed(() => {
  if (!transferts.value?.recipient.length) {
    return null
  }
  return {
    id: `${props.entity.id}-recipient`,
    data: transferts.value.recipient,
    columns: getTableColumns(showAmount.value, transferts.value.recipient, [
      "recipient",
    ]),
    defaultSort: {
      sortField: "date_clc",
      sortOrder: -1,
    },
    header: {
      title: "Transferts received",
    },
    rowUniqueId: "id",
    currencySelector: showAmount.value,
    buttons: buttons,
    exportTitle: exportString,
  }
})

const agentTableProps = computed(() => {
  if (!transferts.value?.agent.length) {
    return null
  }
  return {
    id: `${props.entity.id}-agent`,
    data: transferts.value.agent,
    columns: getTableColumns(showAmount.value, transferts.value.agent, [
      "agent",
    ]),
    defaultSort: {
      sortField: "date_clc",
      sortOrder: -1,
    },
    header: {
      title: "Transferts as an agent",
    },
    rowUniqueId: "id",
    currencySelector: showAmount.value,
    buttons: buttons,
    exportTitle: exportString,
  }
})

const skeletonTableProps = computed(() => {
  return {
    id: `${props.entity.id}-skeleton-table`,
    data: new Array(20).fill({ field: "dummy" }),
    columns: getTableColumns(showAmount.value, []),
    header: {
      title: "Transferts",
    },
    rowUniqueId: "id",
    skeleton: true,
    exportTitle: exportString,
    hideCount: true,
  }
})
</script>

<template>
  <div v-if="props.entity.is_recipient">
    <Tabs v-model:value="activeTab">
      <TabList class="tab-list">
        <Tab value="0" as="button">
          <span class="tab-header">
            <font-awesome-icon class="icon" icon="list-ul" />
            <span>Table</span>
          </span>
        </Tab>
        <Tab value="1" as="button">
          <span class="tab-header">
            <font-awesome-icon class="icon" icon="chart-column" />
            <span>Charts</span>
          </span>
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="0">
          <div v-if="!transferts">
            <!-- @vue-ignore -->
            <Table v-bind="skeletonTableProps"></Table>
          </div>
          <div v-if="transferts">
            <Table v-if="emitterTableProps" v-bind="emitterTableProps"></Table>
            <Table
              v-if="recipientTableProps"
              v-bind="recipientTableProps"
            ></Table>
            <Table v-if="agentTableProps" v-bind="agentTableProps"></Table>
          </div>
        </TabPanel>
        <TabPanel value="1">
          <div class="data-chart-panel">
            <div v-if="chartTabTriggered" class="dataviz-wrapper">
              <EntityHistogram :entity="props.entity" class="entity-chart" />
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
  <div v-else>
    <div v-if="!transferts">
      <!-- @vue-ignore -->
      <Table v-bind="skeletonTableProps"></Table>
    </div>
    <div v-if="transferts">
      <Table v-if="emitterTableProps" v-bind="emitterTableProps"></Table>
      <Table v-if="recipientTableProps" v-bind="recipientTableProps"></Table>
      <Table v-if="agentTableProps" v-bind="agentTableProps"></Table>
    </div>
  </div>
</template>

<style scoped>
.tab-list {
  position: sticky;
  top: var(--header-height);
  z-index: 1;
}
.tab-header {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  gap: 0.6em;
  align-items: center;
  font-size: 1.3em;
}

.data-chart-panel {
  width: 100%;
  overflow-x: auto;
  padding: 1em;
}

.dataviz-wrapper {
  min-width: 300px;
  /* max-width: 100%; */
}
</style>
