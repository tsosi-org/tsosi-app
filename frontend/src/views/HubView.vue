<script setup lang="ts">
import Button from "primevue/button"
import Tab from "primevue/tab"
import TabList from "primevue/tablist"
import TabPanel from "primevue/tabpanel"
import TabPanels from "primevue/tabpanels"
import Tabs from "primevue/tabs"
import { computed, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import NotFound from "@/components/atoms/NotFound.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import HubSupports from "@/components/hub/HubSupports.vue"
import { canEditEntity, logOut, session } from "@/singletons/hub-session"
import { getEntityPreview, type EntityDetails } from "@/singletons/ref-data"
import { changeMetaTitle } from "@/utils/seo"
import { getHubEntityRef } from "@/utils/url-utils"

/**
 * The organization's Hub, in two tabs: its supports table, and its public
 * page's metadata, edited in place. Infrastructures and consortia only have
 * the latter for now. The tab shown is in the URL (`?tab=page`).
 */
const route = useRoute()
const router = useRouter()

changeMetaTitle("Data Contribution Hub")

type HubTab = "supports" | "page"

const organization = ref<EntityDetails | null>(null)
// The TSOSI team on another organization's Hub
const readOnly = ref(false)
const loading = ref(true)
const showSupports = ref(false)

async function loadOrganization(entityId: string) {
  loading.value = true
  // Any organization, public or not
  const preview = await getEntityPreview(entityId)
  const ref = preview && getHubEntityRef(preview.entity)
  if (ref && ref != entityId) {
    // The URL with its TSOSI ID
    router.replace({
      name: route.name!,
      params: { entityId: ref },
      query: route.query,
    })
    return
  }
  readOnly.value = session.member?.organization?.id != preview?.entity.id
  organization.value = preview?.entity ?? null
  loading.value = false
  // Infrastructures and consortia only edit their profile for now
  showSupports.value = readOnly.value || !!session.member?.can_declare_supports
}

watch(
  () => route.params.entityId as string | undefined,
  (entityId) => {
    if (entityId) {
      loadOrganization(entityId)
    }
  },
  { immediate: true },
)

// The organization once its profile is saved, without reloading the Hub
async function onProfileSaved() {
  const preview = await getEntityPreview(organization.value!.id)
  if (preview) {
    organization.value = preview.entity
  }
}

const tab = computed<HubTab>({
  get: () =>
    route.query.tab == "page" || !showSupports.value ? "page" : "supports",
  set: (value) => {
    const query = { ...route.query }
    if (value == "page") {
      query.tab = "page"
    } else {
      delete query.tab
    }
    router.replace({ query })
  },
})

const editable = computed(
  () => !!organization.value && canEditEntity(organization.value.id),
)

async function logOutAndLeave() {
  await logOut()
  router.push({ name: "home" })
}
</script>

<template>
  <Loader v-if="loading" width="150px"></Loader>
  <NotFound v-else-if="!organization"></NotFound>
  <div class="container" v-else>
    <div class="regular-content hub">
      <Message v-if="readOnly">
        You're viewing this organization's Hub as a TSOSI admin, in read-only
        mode.
      </Message>
      <div class="hub-header">
        <h1>{{ organization.name }}</h1>
        <!-- It would also end the admin's Django admin session -->
        <Button
          v-if="!readOnly"
          label="Log out"
          severity="secondary"
          @click="logOutAndLeave"
        />
      </div>
      <Tabs
        :value="tab"
        @update:value="(value) => (tab = String(value) as HubTab)"
      >
        <TabList v-if="showSupports">
          <Tab value="supports" as="button">
            <span class="tab-header">
              <font-awesome-icon :icon="['fas', 'list-ul']" />
              Supports
            </span>
          </Tab>
          <Tab value="page" as="button">
            <span class="tab-header">
              <font-awesome-icon :icon="['fas', 'globe']" />
              Public page
            </span>
          </Tab>
        </TabList>
        <TabPanels class="tab-panels">
          <TabPanel v-if="showSupports" value="supports">
            <HubSupports
              :key="organization.id"
              :organization="organization"
              :readOnly="readOnly"
            />
          </TabPanel>
          <TabPanel value="page">
            <section class="profile" aria-label="Public page">
              <p class="hint">
                The organization's information shown on its
                <RouterLink
                  :to="{ name: 'entity', params: { id: organization.id } }"
                  >public page</RouterLink
                >. Edits are published at once.
              </p>
              <EntityMeta
                :entity="organization"
                :editable="editable"
                profile-only
                @saved="onProfileSaved"
              />
            </section>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  </div>
</template>

<style scoped>
.hub {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hub-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

h1 {
  margin: 0;
}

.tab-header {
  display: flex;
  align-items: center;
  gap: 0.6em;
}

.tab-panels {
  padding-inline: 0;
}

.profile {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hint {
  margin: 0;
  color: var(--p-neutral-600);
}
</style>
