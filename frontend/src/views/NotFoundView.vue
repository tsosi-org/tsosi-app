<script setup lang="ts">
import { useRoute } from "vue-router"
import { changeTitle } from "@/utils/dom-utils"

changeTitle("404 Not found")

const route = useRoute()

const query = route.query
const queriedUrl = query.target || route.path
</script>

<template>
  <div class="container">
    <div class="not-found">
      <p>The queried URL "{{ queriedUrl }}"" does not exist.</p>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  padding: 3rem;
}
</style>
