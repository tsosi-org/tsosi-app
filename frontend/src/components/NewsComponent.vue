<script setup lang="ts">
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
</script>

<template>
  <!-- Detail view -->
  <article class="post" v-if="!props.fullPage">
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
        [Open newsletter]
      </RouterLink>
    </div>
  </article>
  <!-- List view -->
  <article class="post" v-else>
    <h2 class="post-title">{{ title }}</h2>
    <div v-html="props.html"></div>
  </article>
</template>

<style scoped>
.post {
  padding: 35px 0;
  border-style: solid;
  border-color: var(--p-neutral-800);
  border-width: 0 0 1px 0;
}

.post:deep(img) {
  height: auto !important;
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
