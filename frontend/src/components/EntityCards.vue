<script setup lang="ts">
import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityCard from "@/components/EntityCard.vue"
import { type Entity, type Transfer } from "@/singletons/ref-data"
import DataView from "primevue/dataview"
import { onMounted, ref, type Ref } from "vue"

const props = defineProps<{
  role: "emitter" | "recipient"
  entity: Entity
  entities: Entity[]
  transfers: Transfer[] | null
  disableExport?: boolean
}>()
const amounts: Ref<Record<string, Record<string, number>> | null> = ref(null)
const loading = ref(true)
const chartTitle = `${props.role == "emitter" ? "Supported infrastructures" : "Supporters"} - ${props.entity?.short_name || props.entity.name}`

onMounted(async () => {
  await loadData()
  loading.value = false
})

async function loadData() {
  if (!props.transfers) {
    return
  }
  amounts.value = props.transfers
    .filter(
      (transfer) =>
        transfer.amounts_clc && transfer.recipient_id != props.entity.id,
    )
    .reduce((acc: any, transfer) => {
      const entityId =
        props.role == "emitter" ? transfer.recipient_id : transfer.emitter_id
      if (acc[entityId] === undefined) {
        acc[entityId] = { ...transfer.amounts_clc }
      } else {
        for (const currency in transfer.amounts_clc) {
          if (acc[entityId][currency]) {
            acc[entityId][currency] += transfer.amounts_clc[currency]
          } else {
            delete acc[entityId][currency]
          }
        }
      }
      if (transfer.date_clc.dateObj) {
        acc[entityId]["since"] = Math.min(
          acc[entityId]["since"] || new Date().getFullYear(),
          transfer.date_clc.dateObj?.getFullYear() || new Date().getFullYear(),
        )
      }
      return acc
    }, {})
  props.entities.sort((a, b) => {
    // Sort by is_partner, has logo, and name
    const scoreA = (a.is_partner ? 3 : 0) + (a.logo ? 2 : 0)
    const scoreB = (b.is_partner ? 3 : 0) + (b.logo ? 2 : 0)
    return scoreB - scoreA + a.name.localeCompare(b.name)
  })
}

function getFileName(): string {
  const baseName = props.entity.name.replace(/\s+/g, "_")
  const chartTitleClean = chartTitle.replace(/\s+/g, "_")
  return `TSOSI_${baseName}_${chartTitleClean}`
}

async function downloadPNG() {
  alert("Not implemented yet!")
}

async function downloadData(format: "json" | "csv") {
  alert("Not implemented yet!")
}

const exportItems = [
  {
    label: "Export CSV",
    icon: ["fas", "download"],
    command: () => downloadData("csv"),
  },
  {
    label: "Export JSON",
    icon: ["fas", "download"],
    command: () => downloadData("json"),
  },
  {
    label: "Export PNG",
    icon: ["fas", "download"],
    command: () => downloadPNG(),
  },
]
</script>

<template>
  <div class="chart-wrapper">
    <div class="container">
      <Loader v-if="loading" width="200px" />
      <DataView
        v-else
        :value="entities"
        layout="grid"
        dataKey="id"
        paginator
        :rows="40"
        class="entity-dataview"
      >
        <template #grid="slotProps">
          <div class="entities-grid">
            <EntityCard
              v-for="entity in slotProps.items"
              :key="entity.id"
              :entity="entity"
            />
          </div>
        </template>
      </DataView>
    </div>
  </div>
</template>

<style scoped>
.entity-dataview {
  width: 100%;
}

.entities-grid {
  width: 100%;
  height: 100%;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 20px;
}
.chart-wrapper {
  min-width: 300px;
  margin-bottom: 100px;

  & > * {
    margin-top: 1.5rem;
  }

  & > *:first-child {
    margin-top: unset;
  }
}
.chart-header {
  text-align: center;
}

.chart-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  justify-content: center;
  align-items: start;
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  gap: 0.8em;
  justify-content: end;
}

.check-box-wrapper {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.25em;
}

.chart-title {
  font-weight: 900;
}

.chart-description {
  margin-left: auto;
  margin-right: auto;
  width: fit-content;
}
</style>
