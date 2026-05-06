<script setup lang="ts">
import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityData from "@/components/EntityData.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import EntityViz from "@/components/EntityViz.vue"
import { devMode } from "@/singletons/devMode"
import {
  getEntityDetails,
  getEntitySummary,
  getTransfers,
  resolveEntityRoute,
  type EntityDetails,
  type Transfer,
} from "@/singletons/ref-data"
import { formatDateWithPrecision } from "@/utils/data-utils"
import {
  changeMetaDescripion,
  changeMetaTitle,
  changeMetaUrl,
} from "@/utils/dom-utils"
import Tab from "primevue/tab"
import TabList from "primevue/tablist"
import TabPanel from "primevue/tabpanel"
import TabPanels from "primevue/tabpanels"
import Tabs from "primevue/tabs"
import { onBeforeMount, shallowRef, watch, type ShallowRef } from "vue"
import { useRoute, useRouter } from "vue-router"

const entity: ShallowRef<EntityDetails | null> = shallowRef(null)
const transfers: ShallowRef<Transfer[] | null> = shallowRef(null)

onBeforeMount(async () => {
  const route = useRoute()
  const router = useRouter()
  const entityId = resolveEntityRoute(route.params.id as string)

  const result = entityId ? getEntitySummary(entityId) : undefined
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  entity.value = (await getEntityDetails(result.id)) as EntityDetails
})

watch(entity, onEntityChange)

async function onEntityChange() {
  if (!entity.value) {
    return
  }
  transfers.value = await getTransfers(entity.value.id)
  changeMetaTitle(entity.value.name)
  const desc = entity.value.is_recipient
    ? `Explore the funding made to sustain ${entity.value.name}`
    : `Explore the funding performed by ${entity.value.name}`
  changeMetaDescripion(desc)
  changeMetaUrl(true)
}
</script>

<template>
  <Loader v-show="!entity" width="150px"></Loader>
  <div class="container" v-if="entity">
    <div class="regular-content">
      <EntityMeta :entity="entity as EntityDetails" />
      <Tabs lazy value="0" v-if="devMode">
        <TabList class="tab-list">
          <Tab value="0" as="button">
            <span class="tab-header" v-if="entity.is_emitter">
              <font-awesome-icon class="icon" :icon="['fas', 'house']" />
              <span>Infrastructures</span>
            </span>
            <span class="tab-header" v-else>
              <font-awesome-icon class="icon" :icon="['fas', 'house']" />
              <span>Supporters</span>
            </span>
          </Tab>
          <Tab value="1" as="button">
            <span class="tab-header">
              <font-awesome-icon class="icon" :icon="['fas', 'chart-column']" />
              <span>Charts</span>
            </span>
          </Tab>
          <Tab value="2" as="button">
            <span class="tab-header">
              <font-awesome-icon class="icon" :icon="['fas', 'list-ul']" />
              <span>Table</span>
            </span>
          </Tab>
          <div v-if="entity.date_data_update" class="data-update-date">
            <span>
              Last data update:
              {{ formatDateWithPrecision(entity.date_data_update, "day") }}
            </span>
          </div>
        </TabList>
        <TabPanels>
          <TabPanel value="0">
            <EntityViz :entity="entity" :transfers="transfers" cards />
          </TabPanel>
          <TabPanel value="1">
            <EntityViz :entity="entity" :transfers="transfers" />
          </TabPanel>
          <TabPanel value="2">
            <EntityData :entity="entity" :transfers="transfers" />
          </TabPanel>
        </TabPanels>
      </Tabs>
      <Tabs lazy value="0" v-else-if="entity.is_recipient && entity.is_partner">
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
            <EntityData :entity="entity" :transfers="transfers" />
          </TabPanel>
          <TabPanel value="1">
            <EntityViz :entity="entity" :transfers="transfers" />
          </TabPanel>
        </TabPanels>
      </Tabs>
      <EntityData v-else :entity="entity" :transfers="transfers" />
    </div>
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

.data-update-date {
  display: flex;
  margin-left: auto;
  color: var(--p-tabs-tab-hover-color);
  align-items: center;
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
