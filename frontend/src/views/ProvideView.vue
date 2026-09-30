<script setup lang="ts">
import { useRoute } from "vue-router"
const route = useRoute()

const query = ["name", "ror_url"]
  .map(
    (key) =>
      `${encodeURIComponent(key)}=${encodeURIComponent((route.query[key] as string) || "")}`,
  )
  .join("&")

const gristFormUrl = `https://tsosi.getgrist.com/forms/3nGNWU5Pisa2byXGKbVdRq/32?style=singlePage&themeSyncWithOs=false&${query}`
</script>

<template>
  <div class="container">
    <div class="regular-content static-content">
      <h1 class="page-title">Provide your data</h1>
      <iframe :src="gristFormUrl" height="1350px" width="100%" frameborder="0">
      </iframe>
    </div>
  </div>
</template>

<style scoped>
.static-content h1.page-title {
  font-size: 2.5rem;
  text-align: center;
  padding: 0;
}

.static-content {
  margin-bottom: 2rem;
  font-size: 1.15rem;

  & :deep(h2) {
    font-size: 1.5em;
  }

  & :deep(h1),
  & :deep(h2),
  & :deep(h3),
  & :deep(h4),
  & :deep(h5),
  & :deep(h6) {
    margin: 1.65em 0 0.35em 0;
    padding: 0.35em 0;
  }

  & h1.page-title {
    margin: 1em 0;
  }
}
</style>
