<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import NewsSubButtonAtom from "@/components/atoms/NewsSubButtonAtom.vue"
import type { Post } from "@/components/NewsComponent.vue"
import NewsComponentVue from "@/components/NewsComponent.vue"
import { get } from "@/services/api"
import StaticContentComponent from "@/views/StaticContentView.vue"

// Newsletters stored hourly by the backend (`tsosi/data/newsletters.py`)
interface NewsletterApiEntry {
  id: string
  date: string
  key_points: string[]
  html?: string
}

const newsletters = ref<Post[]>([])
const newsletter = ref<Post>()
const loading = ref<boolean>(true)
const router = useRouter()
const route = useRoute()

function toPost(entry: NewsletterApiEntry): Post {
  return {
    id: entry.id,
    date: new Date(entry.date),
    keyPoints: entry.key_points,
    html: entry.html,
  }
}

onBeforeMount(async () => {
  if (route.params.id) {
    const result = await get(`newsletters/${route.params.id}`, true)
    if (result.error || !result.data) {
      router.replace({ name: "NotFound", query: { target: route.path } })
      return
    }
    newsletter.value = toPost(result.data as NewsletterApiEntry)
  } else {
    const result = await get("newsletters", true)
    if (!result.error && Array.isArray(result.data)) {
      newsletters.value = (result.data as NewsletterApiEntry[]).map(toPost)
    }
  }
  loading.value = false
})
</script>

<template>
  <StaticContentComponent title="Newsletter">
    <NewsSubButtonAtom />
    <div v-if="!loading">
      <!-- Detail view -->
      <div v-if="newsletter">
        <RouterLink to="/pages/newsletter">
          <font-awesome-icon :icon="['fas', 'chevron-left']" />
          All newsletters
        </RouterLink>
        <NewsComponentVue v-bind="newsletter" full-page />
      </div>
      <!-- List view -->
      <div v-else>
        <NewsComponentVue v-for="n in newsletters" :key="n.id" v-bind="n" />
      </div>
    </div>
  </StaticContentComponent>
</template>

<style scoped></style>
