<script setup lang="ts">
import { computed, onMounted, ref, watch, type Ref } from "vue"

import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityCards from "@/components/EntityCards.vue"
import EntityContinentHistogram from "@/components/EntityContinentHistogram.vue"
import EntityHistogramInstitution from "@/components/EntityHistogramInstitution.vue"
import EntityMap from "@/components/EntityMap.vue"
import EntityTimeline from "@/components/EntityTimeline.vue"
import EntityTreemapInstitution from "@/components/EntityTreemapInstitution.vue"
import {
  getEntitiesFromTransfers,
  type Entity,
  type EntityDetails,
  type Transfer,
} from "@/singletons/ref-data"
import Divider from "primevue/divider"

const props = defineProps<{
  entity: EntityDetails
  transfers: Transfer[] | null
  cards?: boolean
}>()

const loading = ref(true)
const entities: Ref<Record<string, Entity[]> | null> = ref(null)
const safeEntities = computed(() => {
  return (
    entities.value || {
      emitters: [],
      recipients: [],
    }
  )
})
const safeTransfers = computed(() => props.transfers || [])

// Whether to display the histogram
const noHistogramIds =
  import.meta.env.VITE_INFRA_HISTOGRAM_OPT_OUT?.split(",") || []

const displayHistogram = computed(() => {
  if (!noHistogramIds.length) {
    return true
  }
  return !props.entity.identifiers.some((id) =>
    noHistogramIds.includes(id.value),
  )
})

function loadData() {
  if (props.transfers) {
    entities.value = getEntitiesFromTransfers(props.transfers)
    loading.value = false
  }
}

onMounted(async () => {
  loadData()
})

watch(
  () => props.transfers,
  () => {
    loadData()
  },
)
</script>

<template>
  <Loader v-if="loading" width="150px"></Loader>
  <div v-else class="data-chart-panel">
    <EntityCards
      v-if="cards"
      role="emitter"
      :entity="props.entity"
      :entities="
        props.entity.is_recipient
          ? safeEntities.emitters
          : safeEntities.recipients
      "
      :transfers="safeTransfers"
      class="entity-chart"
    />
    <EntityTreemapInstitution
      v-if="!props.entity.is_recipient && !cards"
      role="emitter"
      :entity="props.entity"
      :entities="safeEntities.recipients"
      :transfers="safeTransfers"
      class="entity-chart"
    />
    <Divider v-if="!props.entity.is_recipient && !cards" />
    <EntityHistogramInstitution
      v-if="!props.entity.is_recipient && !cards"
      :entity="props.entity"
      :transfers="safeTransfers"
      class="entity-chart"
    />
    <Divider v-if="!props.entity.is_recipient && !cards" />
    <EntityTimeline
      v-if="!props.entity.is_recipient && !cards"
      :entity="props.entity"
      :entities="safeEntities.recipients"
      :transfers="safeTransfers"
      class="entity-chart"
    />
    <Divider v-if="!props.entity.is_recipient && !cards" />
    <EntityMap
      v-if="!cards"
      :id="`entity-map-${props.entity.id}`"
      :supporters="
        props.entity.is_recipient ? safeEntities.emitters : [props.entity]
      "
      :infrastructures="
        props.entity.is_recipient ? [] : safeEntities.recipients
      "
      :title="`Location of the ${props.entity.is_recipient ? 'supporters' : 'infrastructures'}`"
      :data-loaded="true"
      :export-title-base="props.entity.name"
      :disableLegend="true"
      :disableExport="true"
    />
    <Divider v-if="props.entity.is_recipient && !cards && displayHistogram" />
    <EntityContinentHistogram
      v-if="props.entity.is_recipient && !cards && displayHistogram"
      :entity="props.entity"
      class="entity-chart"
    />
  </div>
</template>

<style scoped>
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

.transfer-tables:deep(a.entity-link) {
  text-decoration: underline;
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
