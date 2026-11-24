<script setup lang="ts">
import Button from "primevue/button"
import Tab from "primevue/tab"
import TabList from "primevue/tablist"
import TabPanel from "primevue/tabpanel"
import TabPanels from "primevue/tabpanels"
import Tabs from "primevue/tabs"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import NotFound from "@/components/atoms/NotFound.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import HubSupports from "@/components/hub/HubSupports.vue"
import {
  canDeclareSupports,
  canEditEntity,
  logOut,
  session,
} from "@/singletons/hub-session"
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

type HubTab = "support" | "page"

const organization = ref<EntityDetails | null>(null)
// The user's own organization, else the TSOSI team on another
// organization's Hub
const ownOrganization = ref(false)
// The supports, unless `canDeclareSupports`: the TSOSI team only reads them,
// except the superusers. The public page is editable (`canEditEntity`).
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
  ownOrganization.value = session.member?.organization?.id == preview?.entity.id
  readOnly.value = !preview || !canDeclareSupports(preview.entity)
  organization.value = preview?.entity ?? null
  loading.value = false
  // Infrastructures and consortia only edit their profile for now
  showSupports.value = !ownOrganization.value || !readOnly.value
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
    route.query.tab == "page" || !showSupports.value ? "page" : "support",
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

const supportsIntro = computed(() =>
  readOnly.value
    ? "These are all the support we currently list for your organization."
    : "These are all the support we currently list for your organization. You can " +
      "edit or declare new ones. Your changes stay in draft until you " +
      "submit them, then the TSOSI team will review and publish the changes.",
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
      <template v-if="!ownOrganization">
        <Message>
          You're viewing this organization's Hub as a TSOSI admin.
        </Message>
      </template>
      <div class="hub-header">
        <h1>{{ organization.name }}</h1>
        <Button
          v-if="ownOrganization"
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
          <Tab value="support" as="button">
            <span class="tab-header">
              <font-awesome-icon :icon="['fas', 'list-ul']" />
              Support
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
          <TabPanel v-if="showSupports" value="support">
            <p class="tab-intro">{{ supportsIntro }}</p>
            <HubSupports
              :key="organization.id"
              :organization="organization"
              :readOnly="readOnly"
            />
          </TabPanel>
          <TabPanel value="page">
            <p class="tab-intro">
              This is how your organization appears publicly on TSOSI.
            </p>
            <section class="profile" aria-label="Public page">
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

.tab-intro {
  max-width: 50rem;
  margin: 0 0 1.5rem;
  color: var(--p-text-muted-color);
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
