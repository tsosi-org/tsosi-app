<script setup lang="ts">
import {
  getEntityDetails,
  getEntitySummary,
  getTransferts,
  type EntityDetails,
  type DeepReadonly,
  type Transfert,
  type TransfertEntityType,
} from "@/singletons/ref-data"
import { useRoute, useRouter } from "vue-router"
import { ref, type Ref, onBeforeMount, watch, computed } from "vue"
import { changeTitle } from "@/utils/dom-utils"
import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { getEntityBaseUrl, getTransfertBaseUrl } from "@/utils/url-utils"
import { selectedCurrency } from "@/singletons/currencyStore"
import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import { fillTransfertAmountCurrency } from "@/utils/data-utils"

const route = useRoute()
const router = useRouter()

const entity: Ref<DeepReadonly<EntityDetails> | null> = ref(null)
const transferts: Ref<Record<TransfertEntityType, Transfert[]> | null> =
  ref(null)
const showAmount: Ref<boolean> = ref(true)

onBeforeMount(async () => {
  const result = await getEntitySummary(route.params.id as string)
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  entity.value = await getEntityDetails(route.params.id as string)
})

async function update_transferts() {
  if (!entity.value) {
    return
  }

  const rawTransferts = await getTransferts(entity.value.id)
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
    if (transfert.emitter_id == entity.value.id) {
      sortedTransferts["emitter"].push(transfert)
    } else if (transfert.recipient_id == entity.value.id) {
      sortedTransferts["recipient"].push(transfert)
    } else if (transfert.agent_id == entity.value.id) {
      sortedTransferts["agent"].push(transfert)
    } else {
      console.warn(
        `Following transfert does not involve entity ${entity.value.id}: ${transfert}`,
      )
    }
  }
  showAmount.value = transfertWithAmount
  transferts.value = sortedTransferts
}

async function onEntityChange() {
  if (!entity.value) {
    return
  }
  changeTitle(entity.value.name)
  await update_transferts()
}

watch(entity, onEntityChange)
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

const emitterTableProps = computed(() => {
  if (!entity.value || !transferts.value?.emitter.length) {
    return null
  }
  return {
    id: `${entity.value.id}-emitter`,
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
    exportTitle: `TSOSI_${entity.value.name.replace(/\s+/g, "_")}`,
  }
})

const recipientTableProps = computed(() => {
  if (!entity.value || !transferts.value?.recipient.length) {
    return null
  }
  return {
    id: `${entity.value.id}-recipient`,
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
    exportTitle: `TSOSI_${entity.value.name.replace(/\s+/g, "_")}`,
  }
})

const agentTableProps = computed(() => {
  if (!entity.value || !transferts.value?.agent.length) {
    return null
  }
  return {
    id: `${entity.value.id}-agent`,
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
    exportTitle: `TSOSI_${entity.value.name.replace(/\s+/g, "_")}`,
  }
})

const skeletonTableProps = computed(() => {
  if (!entity.value) {
    return null
  }
  return {
    id: `${entity.value.id}-skeleton-table`,
    data: new Array(20).fill({ field: "dummy" }),
    columns: getTableColumns(showAmount.value, []),
    header: {
      title: "Transferts",
    },
    rowUniqueId: "id",
    skeleton: true,
    exportTitle: `TSOSI_${entity.value.name.replace(/\s+/g, "_")}`,
  }
})
</script>

<template>
  <Loader v-show="!entity" width="150px"></Loader>
  <div class="container" v-if="entity">
    <div class="regular-content">
      <EntityMeta :entity="entity"></EntityMeta>
      <div class="transferts">
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
      </div>
    </div>
  </div>
</template>
