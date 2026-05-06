<script setup lang="ts">
import { computed, ref } from "vue"

import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import { selectedCurrency } from "@/singletons/currencyStore"
import { type EntityDetails, type Transfer } from "@/singletons/ref-data"
import { getTransferBaseUrl } from "@/utils/url-utils"

const props = defineProps<{
  entity: EntityDetails
  transfers: Transfer[] | null
}>()

// There seems to be Memory leak because of the datatable component,
// mainly caused by this skeleton table.
const displaySkeletonTable = ref(true)

const currencyColumn = "__currency"
const amountColumn = "__amount"
const baseColumns: TableColumnProps[] = [
  {
    id: "date_clc",
    title: "Date",
    field: "date_clc",
    type: "dateWithPrecision",
    sortable: true,
    info: "The date field is relative. <a href='/pages/faq#what-does-the-date-column-refer-to'>See our FAQ</a>",
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
    id: "agents",
    title: "Intermediary",
    field: "agents",
    type: "entityLink",
    labelGetter: (item: any) =>
      item.agents
        ?.map(
          (agent: any) =>
            `${agent?.name}` +
            (agent?.short_name ? ` (${agent.short_name})` : ""),
        )
        .join(", ") || "",
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
    labelGetter: (item: any) =>
      `${item.recipient?.name}` +
      (item.recipient?.short_name ? ` (${item.recipient.short_name})` : ""),
    sortable: true,
    filter: {
      enable: true,
    },
  },
  {
    id: "amount",
    title: "Amount",
    labelGetter: (row) => row.amounts_clc?.[selectedCurrency.value.id] ?? null,
    field: amountColumn,
    type: "number",
    sortable: true,
    nullValueTemplate: '<span class="data-label hidden-amount">hidden</span>',
    info: "The amount of the support may be hidden. See <a href='/pages/faq#amounts-hidden'>the FAQ</a>",
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
  if (!props.transfers) {
    return null
  }
  let toRemoveCols: string[] = []
  if (props.transfers.every((t) => t.amount == null)) {
    toRemoveCols.push("currency")
    if (props.entity.is_recipient) {
      toRemoveCols.push("amount")
    }
  }
  if (props.transfers.every((t) => t.agent_ids.length == 0)) {
    toRemoveCols.push("agents")
  }
  if (props.transfers.every((t) => t.emitter_id == props.entity.id)) {
    toRemoveCols.push("emitter")
  }
  if (!props.entity.is_recipient) {
    toRemoveCols.push("emitterCountry")
  }
  if (props.transfers.every((t) => t.recipient_id == props.entity.id)) {
    toRemoveCols.push("recipient")
  }

  return {
    id: `${props.entity.id}-transfers`,
    data: props.transfers,
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
</script>

<template>
  <div v-if="!transfers && displaySkeletonTable" class="transfer-tables">
    <Table v-bind="skeletonTableProps"></Table>
  </div>
  <div v-if="transfers" class="transfer-tables">
    <Table v-if="tableProps" v-bind="tableProps"></Table>
  </div>
</template>

<style scoped>
.transfer-tables > * {
  margin-bottom: 2em;
}

.transfer-tables > *:last-child {
  margin-bottom: initial;
}

.transfer-tables:deep(a.entity-link) {
  text-decoration: underline;
}
</style>
