<script setup lang="ts">
import { computed, ref } from "vue"

import type { ButtonProps } from "@/components/atoms/ButtonAtom.vue"
import Table from "@/components/TableComponent.vue"
import { type EntityDetails, type Transfer } from "@/singletons/ref-data"
import {
  hiddenTransferColumns,
  transferColumns,
  transferDetailsButton,
} from "@/utils/transfer-table"

const props = defineProps<{
  entity: EntityDetails
  transfers: Transfer[] | null
}>()

// There seems to be Memory leak because of the datatable component,
// mainly caused by this skeleton table.
const displaySkeletonTable = ref(true)

const baseColumns = transferColumns()
const buttons: Array<ButtonProps> = [transferDetailsButton]

const exportString = `TSOSI_${props.entity.name.replace(/\s+/g, "_")}`
// Config for the transfer table
const tableProps = computed(() => {
  if (!props.transfers) {
    return null
  }
  const toRemoveCols = hiddenTransferColumns(props.entity, props.transfers)

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
    urlState: true,
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
