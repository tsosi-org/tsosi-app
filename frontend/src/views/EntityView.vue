<script setup lang="ts">
import { onBeforeMount, ref, shallowRef, type Ref, type ShallowRef } from "vue"
import { useRoute, useRouter } from "vue-router"
import Tab from "primevue/tab"
import TabList from "primevue/tablist"
import TabPanel from "primevue/tabpanel"
import TabPanels from "primevue/tabpanels"
import Tabs from "primevue/tabs"
import { computed, watch } from "vue"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import NotFound from "@/components/atoms/NotFound.vue"
import EntityData from "@/components/EntityData.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import EntityViz from "@/components/EntityViz.vue"
import { devMode } from "@/singletons/devMode"
import {
  getEntityDetails,
  getEntityPreview,
  getEntitySummary,
  getTransfers,
  resolveEntityRoute,
  type EntityDetails,
  type PreviewReason,
  type Transfer,
} from "@/singletons/ref-data"
import { canEditEntity, loadSession, session } from "@/singletons/hub-session"
import { formatDateWithPrecision } from "@/utils/data-utils"
import {
  changeCanonicalUrl,
  changeMetaDescription,
  changeMetaTitle,
} from "@/utils/seo"
import { getEntityUrl } from "@/utils/url-utils"

const route = useRoute()
const router = useRouter()
const entity: ShallowRef<EntityDetails | null> = shallowRef(null)
const transfers: ShallowRef<Transfer[] | null> = shallowRef(null)
const loading = ref(true)
// Opened with the edit link (`?edit`), from the Hub or the admin
const startEditing = ref(route.query.edit !== undefined)
// Set when the entity is not on the public site yet: the page is a preview,
// for its members and the TSOSI team only.
const previewReason: Ref<PreviewReason | null> = ref(null)
const editable = computed(
  () => entity.value != null && canEditEntity(entity.value.id),
)

const previewMessages: Record<PreviewReason, string> = {
  to_check:
    "It will be published once TSOSI's curation board has added the infrastructure to its scope.",
  out_of_scope: "The infrastructure is not in TSOSI's scope.",
  no_public_support:
    "It will be published with the organization's first public support.",
}

onBeforeMount(async () => {
  const entityId = resolveEntityRoute(route.params.id as string)
  const result = entityId ? getEntitySummary(entityId) : undefined
  const tsosiId = result?.identifiers.find((i) => i.registry === "tsosi")?.value
  if (tsosiId && tsosiId !== route.params.id) {
    // The page is remounted on the new path: keep the query (`?edit`)
    router.replace({
      name: "entity",
      params: { id: tsosiId },
      query: route.query,
      hash: route.hash,
    })
    return
  }
  // The session is only checked when needed (opened with the edit link, or
  // already loaded), so that public visitors don't make an extra request.
  const checkSession = startEditing.value || session.loaded
  if (result != null) {
    entity.value = (await getEntityDetails(result.id)) as EntityDetails
  } else if (checkSession && (await loadSession())) {
    await loadPreview(route.params.id as string)
  }
  loading.value = false
  if (startEditing.value) {
    await loadSession()
  }
})

async function loadPreview(id: string) {
  const preview = await getEntityPreview(id)
  if (preview) {
    entity.value = preview.entity
    previewReason.value = preview.reason
  }
}

async function onEditSaved() {
  startEditing.value = false
  if (previewReason.value) {
    await loadPreview(entity.value!.id)
  } else {
    entity.value = (await getEntityDetails(entity.value!.id)) as EntityDetails
  }
}

watch(entity, onEntityChange)

async function onEntityChange() {
  if (!entity.value) {
    return
  }
  if (previewReason.value) {
    changeMetaTitle(`${entity.value.name} (preview)`)
    transfers.value = []
    return
  }
  changeMetaTitle(entity.value.name)
  const desc = entity.value.is_recipient
    ? `Explore the funding made to sustain ${entity.value.name}`
    : `Explore the funding performed by ${entity.value.name}`
  changeMetaDescription(desc)
  changeCanonicalUrl(getEntityUrl(entity.value))
  transfers.value = await getTransfers(entity.value)
}
</script>

<template>
  <Loader v-if="loading" width="150px"></Loader>
  <NotFound v-else-if="!entity"></NotFound>
  <div class="container" v-else>
    <div class="regular-content">
      <Message v-if="previewReason" severity="warn" class="preview-banner">
        <strong>Preview: this page isn't public yet.</strong>
        {{ previewMessages[previewReason] }} Only the organization's members and
        the TSOSI team can see it.
      </Message>
      <EntityMeta
        :entity="entity as EntityDetails"
        :editable="editable"
        :start-editing="startEditing"
        :profile-only="!!previewReason"
        @saved="onEditSaved"
      />
      <template v-if="previewReason"></template>
      <Tabs lazy value="0" v-else-if="devMode">
        <TabList class="tab-list">
          <Tab value="0" as="button">
            <span class="tab-header" v-if="!entity.is_recipient">
              <font-awesome-icon class="icon" :icon="['fas', 'house']" />
              <span>Infrastructures</span>
            </span>
            <span class="tab-header" v-else>
              <font-awesome-icon class="icon" :icon="['fas', 'house']" />
              <span>Supporters</span>
            </span>
          </Tab>
          <Tab
            value="1"
            as="button"
            v-if="entity.is_recipient && entity.is_partner"
          >
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
            <p v-if="entity.is_recipient" class="subtitle">
              Institutions that have financially supported
              {{ entity?.short_name || entity.name }}.
            </p>
            <p v-else class="subtitle">
              Open science infrastructures that have been financially supported
              by
              {{ entity?.short_name || entity.name }}.
            </p>
            <EntityViz :entity="entity" :transfers="transfers" cards />
          </TabPanel>
          <TabPanel value="1">
            <EntityViz :entity="entity" :transfers="transfers" />
          </TabPanel>
          <TabPanel value="2">
            <p class="subtitle">
              Individual transfers
              {{ entity.is_recipient ? "received" : "sent" }} by
              {{ entity?.short_name || entity.name }}.
            </p>
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
.preview-banner {
  margin-bottom: 1rem;
}

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

.subtitle {
  position: relative;
  font-weight: 400;
  top: -0.8em;
  font-style: italic;
  color: var(--p-tabs-tab-hover-color);
  margin-bottom: 1.5em;
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
