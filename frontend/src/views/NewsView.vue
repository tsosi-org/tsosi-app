<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import NewsSubButtonAtom from "@/components/atoms/NewsSubButtonAtom.vue"
import type { Post } from "@/components/NewsComponent.vue"
import NewsComponentVue from "@/components/NewsComponent.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"


interface NewsLetterApiEntry {
  name: string
  download_url: string
  type: string
}

const newsletters = ref<Post[]>([])
const newsletter = ref<Post>()
const loading = ref<boolean>(true)
const router = useRouter()
const route = useRoute()

onBeforeMount(async () => {
  if (!import.meta.env.VITE_NEWSLETTERS_URL) {
    loading.value = false
    return
  }
  // Fetch newsletters from NEWSLETTERS_URL
  const res = await fetch(
    import.meta.env.VITE_NEWSLETTERS_URL
  )
  const data: NewsLetterApiEntry[] = await res.json()
  newsletters.value = data.filter(
    n => n.type == "file" && n.name.endsWith(".html")
  ).map((n) => {
    return {
      id: n.name.replace(".html", ""),
      date: new Date(n.name.substring(0, 7)),
      download_url: n.download_url
    }
  }).sort((a, b) => b.date.getTime() - a.date.getTime())
  // Retrieve specific newsletter if id param is present
  if (route.params.id) {
    newsletter.value = newsletters.value.find(n => n.id === route.params.id)
    if (newsletter.value == null) {
      router.replace({ name: "NotFound", query: { target: route.path } })
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