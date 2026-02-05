<script setup lang="ts">
import PostMeta from "@/components/atoms/PostMetaAtom.vue"
import { type Navigation } from "@/views/BlogView.vue"

export interface Post {
  id: string
  title: string
  author: string
  readingTime: number
  summary: string
  date: Date
  htmlContent?: string
  navigation?: Navigation
}
interface Props extends Post {
  fullPage?: boolean
}
const props = defineProps<Props>()
</script>

<template>
  <!-- List view -->
  <article class="post post-entry" v-if="!props.fullPage">
    <RouterLink :to="`/pages/blog/${props.id}/`">
      <h2 class="post-title">{{ props.title }}</h2>
    </RouterLink>
    <PostMeta class="post-meta" :date="props.date" :readingTime="props.readingTime" :author="props.author"></PostMeta>
    <div>
      <div class="post-desc" v-html="props.summary">
      </div>
      <RouterLink class="post-read-more" :to="`/pages/blog/${props.id}/`">
        [Read More]
      </RouterLink>
    </div>
  </article>
  <!-- Detail view -->
  <article class="post post-detail" v-else>
    <h2 class="post-title">{{ props.title }}</h2>
    <PostMeta class="post-meta" :date="props.date" :readingTime="props.readingTime" :author="props.author"></PostMeta>
    <div class="post-content" v-html="props.htmlContent"></div>
    <div class="last-modified">
      Last updated on {{ props.date.toISOString().split('T')[0] }}
    </div>
  </article>
</template>

<style scoped>
.post-entry {
  padding: 35px 0;
  border-style: solid;
  border-color: var(--p-neutral-800);
  border-width: 0 0 1px 0;
}

.post-entry:last-child {
  border-bottom: 0;
}

h2.post-title {
  font-size: 30px;
  font-weight: 800;
  padding: 0;
  margin: 0;
  color: var(--p-primary-800);
  line-height: normal;
}

a > .post-title:hover {
  color: var(--p-primary-600);
}

.post-meta {
  font-size: 1rem;
  color: var(--p-neutral-500);
  font-style: italic;
}

.last-modified {
  margin-top: 2rem;
  font-size: 1rem;
  color: var(--p-neutral-500);
  text-align: right;
  width: 100%;
}

.post-detail > .post-meta {
  font-size: 15px;
}

.post-desc {
  margin-top: 1rem;
  font-size: 1.1rem;
  line-height: 1.6;
}

a, .post:deep(a) {
  color: var(--p-primary-500);
  text-decoration: none;
}

a:hover,
.post:deep(a):hover {
  color: var(--p-primary-800);
}

.post-read-more {
  float: right;
  font-weight: bold;
}

.post-detail {
  padding: 35px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.post-content {
  padding: 35px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.post-detail:deep(div > a > img) {
  display: block;
  margin: auto;
}

.post-content:deep(p), .post-content:deep(h1), .post-content:deep(h2), .post-content:deep(h3), .post-content:deep(h4), .post-content:deep(h5), .post-content:deep(h6) {
  width: 100%;
  text-align: justify;
}

.post:deep(blockquote) {
  border-left: 4px solid var(--p-neutral-300);
  padding-left: 1rem;
  margin-left: 0;
  color: var(--p-neutral-500);
  font-style: italic;
}


</style>