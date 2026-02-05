<script setup lang="ts">
import { onMounted, ref } from "vue"


export interface Post {
  id: string
  date: Date
  download_url: string
}
interface Props extends Post {
  fullPage?: boolean
}
const props = defineProps<Props>()
const html_content = ref<string>("")
const keypoints = ref<string[]>([])
const title = `${props.date.toLocaleString('default', { month: 'long' })} ${props.date.getFullYear()}`

onMounted(async () => {
  const res = await fetch(props.download_url)
  const raw_html = await res.text()
  const dom = document.createElement('html');
  dom.innerHTML = raw_html;
  keypoints.value = dom.querySelectorAll('h2,h3').length > 0
    ? Array.from(dom.querySelectorAll('h2,h3')).map(h2 => h2.textContent?.trim() || "")
    : [];
  html_content.value = dom.querySelector('body')?.innerHTML || "";
})
</script>

<template>
  <!-- Detail view -->
  <article class="post" v-if="!props.fullPage">
    <RouterLink :to="`/pages/newsletter/${props.id}`">
      <h2 class="post-title">{{ title }}</h2>
    </RouterLink>
    <div>
      <div class="post-desc" v-if="keypoints.length > 0">
        <p class="post-desc-intro">Keypoints:</p>
        <ul>
          <li v-for="(kp, index) in keypoints" :key="index">{{ kp }}</li>
        </ul>
      </div>
      <RouterLink class="post-read-more" :to="`/pages/newsletter/${props.id}`">
        [Open newsletter]
      </RouterLink>
    </div>
  </article>
  <!-- List view -->
  <article class="post" v-else>
    <h2 class="post-title">{{ title }}</h2>
    <div v-html="html_content"></div>
  </article>
</template>

<style scoped>
.post {
  padding: 35px 0;
  border-style: solid;
  border-color: var(--p-neutral-800);
  border-width: 0 0 1px 0;
}

.post:last-child {
  border-bottom: 0;
}

h2.post-title {
  font-size: 30px;
  font-weight: 800;
  padding: 0;
  margin: 0;
  color: var(--p-primary-800);
}

.post-title:hover {
  color: var(--p-primary-600);
}

.post-meta {
  font-size: 1rem;
  color: var(--p-neutral-600);
  font-style: italic;
  margin: 0 0 10px !important;
}

.post-desc-intro {
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.post-desc {
  font-size: 1.1rem;
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