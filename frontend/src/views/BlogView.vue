<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import type { Post } from "@/components/BlogComponent.vue"
import BlogComponentVue from "@/components/BlogComponent.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"


interface BlogApiEntry {
  title: string
  author: string
  date: string
  readingTime: number
  summary: string
  permalink: string
}

interface BlogApiResponse {
  posts: BlogApiEntry[]
}

export interface Navigation {
  has_next: boolean
  has_prev: boolean
  next: {
    title: string
    permalink: string
  } | undefined,
  prev: {
    title: string
    permalink: string
  } | undefined
}

interface BlogApiDetail {
  title: string
  author: string
  date: string
  lastmod: string
  readingTime: number
  content: string
  navigation: Navigation
}

const posts = ref<Post[]>([])
const post = ref<Post>()
const loading = ref<boolean>(true)
const router = useRouter()
const route = useRoute()

onBeforeMount(async () => {
  // Fetch posts
  // Retrieve specific post if id param is present
  if (route.params.id) {
    const res = await fetch("/pages/blog/" + route.params.id + "/index.json")
    if (!res.ok) {
      router.push("/pages/blog/")
      return
    }
    const data: BlogApiDetail = await res.json().catch(() => {
      return undefined
    })
    if (!data) {
      router.push("/pages/blog/")
      return
    }
    post.value = {
      id: route.params.id as string,
      title: data.title,
      author: data.author,
      readingTime: data.readingTime,
      summary: data.content,
      date: new Date(data.date),
      htmlContent: data.content,
      navigation: {
        ...data.navigation,
        next: data.navigation.has_next && data.navigation.next ? {
          ...data.navigation.next, 
          permalink: data.navigation.next.permalink.split("/")[2]
        } : undefined,
        prev: data.navigation.has_prev && data.navigation.prev ? {
          ...data.navigation.prev, 
          permalink: data.navigation.prev.permalink.split("/")[2]
        } : undefined,
      }
    }
  }
  else {
    const res = await fetch("/pages/blog/index.json")
    if (!res.ok) {
      router.push("/")
      return
    }
    const data: BlogApiResponse = await res.json().catch(() => {
      return {"posts": []}
    })
    posts.value = data.posts.map((entry) => {
      return {
        id: entry.permalink.split("/")[2],
        title: entry.title,
        summary: entry.summary,
        author: entry.author,
        readingTime: entry.readingTime,
        date: new Date(entry.date),
      }
    })
  }
  loading.value = false
})
</script>


<template>
  <StaticContentComponent title="Blog">
    <div v-if="!loading">
      <!-- Detail view -->
      <div v-if="post">
        <RouterLink to="/pages/blog">
          <font-awesome-icon :icon="['fas', 'chevron-left']" />
          All posts
        </RouterLink>
        <BlogComponentVue v-bind="post" full-page />
      </div>
      <!-- List view -->
      <div v-else-if="posts.length > 0">
        <BlogComponentVue v-for="n in posts" :key="n.id" v-bind="n" />
      </div>
      <!-- Empty state -->
      <p class="empty-state" v-else>
        No posts yet. Check back later!
      </p>  
    </div>
  </StaticContentComponent>
</template>

<style scoped>

.empty-state {
  text-align: center;
}
</style>