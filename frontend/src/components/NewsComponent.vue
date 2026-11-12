<script setup lang="ts">
import { computed } from "vue"

export interface Post {
  id: string
  date: Date
  keyPoints: string[]
  // HTML content of the newsletter, only for the detail view
  html?: string
}
interface Props extends Post {
  fullPage?: boolean
}
const props = defineProps<Props>()
const title = `${props.date.toLocaleString("default", { month: "long", timeZone: "UTC" })} ${props.date.getUTCFullYear()}`

// Drop the newsletter's footer: the first <hr> or <footer> (or its wrapper
// holding nothing else) and everything after it.
function removeFooter(body: HTMLElement) {
  let node: Element | null = body.querySelector("hr, footer")
  while (
    node?.parentElement &&
    node.parentElement !== body &&
    node.parentElement.childElementCount === 1
  ) {
    node = node.parentElement
  }
  while (node) {
    const next: Element | null = node.nextElementSibling
    node.remove()
    node = next
  }
}

const content = computed(() => {
  if (!props.html) return ""
  const body = document.createElement("div")
  body.innerHTML = props.html
  removeFooter(body)
  return body.innerHTML
})
</script>

<template>
  <!-- Detail view -->
  <article class="post post-entry" v-if="!props.fullPage">
    <RouterLink :to="`/pages/newsletter/${props.id}`">
      <h2 class="post-title">{{ title }}</h2>
    </RouterLink>
    <div>
      <div class="post-desc" v-if="props.keyPoints.length > 0">
        <p class="post-desc-intro">Keypoints:</p>
        <ul>
          <li v-for="(kp, index) in props.keyPoints" :key="index">
            {{ kp }}
          </li>
        </ul>
      </div>
      <RouterLink class="post-read-more" :to="`/pages/newsletter/${props.id}`">
        [Read more]
      </RouterLink>
    </div>
  </article>
  <!-- List view -->
  <article class="post post-detail" v-else>
    <h2 class="post-title">{{ title }}</h2>
    <div class="post-content" v-html="content"></div>
  </article>
</template>

<style scoped>
.post-entry {
  padding: 35px 0;
  border-style: solid;
  border-color: var(--p-neutral-800);
  border-width: 0 0 1px 0;
}

.post:deep(img) {
  height: auto !important;
}

.post-entry:last-child {
  border-bottom: 0;
}

h2.post-title {
  font-size: var(--text-xl);
  font-weight: 800;
  padding: 0;
  margin: 0;
  color: var(--p-primary-800);
  line-height: normal;
}

.post-title:hover {
  color: var(--p-primary-600);
}

.post-meta {
  font-size: var(--text-sm);
  color: var(--p-neutral-600);
  font-style: italic;
  margin: 0 0 10px !important;
}

.post-desc-intro {
  font-weight: bold;
  margin: 0 0 0.5rem;
}

.post-desc ul {
  margin: 0;
}

.post-detail {
  max-width: 600px;
  margin: 0 auto;
  padding: 35px 0 2rem;
}

.post-detail > .post-title {
  text-align: center;
}

.post-content {
  padding-top: 1rem;
}

.post-desc {
  margin-top: 1rem;
  font-size: var(--text-base);
  line-height: 1.6;
}

a,
.post-desc:deep(a) {
  color: var(--p-primary-500);
  text-decoration: none;
}

a:hover,
.post-desc:deep(a):hover {
  color: var(--p-primary-800);
}

.post-read-more {
  float: right;
  font-weight: bold;
}
</style>
