<script setup lang="ts">
import { useRoute } from "vue-router"

import { changeMetaTitle } from "@/utils/dom-utils"
import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"


changeMetaTitle("404 Not found")

const route = useRoute()

const query = route.query
const queriedUrl = query.target || route.path
const params = {
  content: queriedUrl as string,
  inline: true,
  background: true,
}
</script>

<template>
  <div class="container">
    <div class="regular-content">
      <h1>404 - Not found</h1>
      <div class="not-found">
        <p>The queried URL <CodeBlockAtom v-bind="params" /> does not exist.</p>
        <p>Go back to the <RouterLink :to="'/'">home page</RouterLink>.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 {
  text-align: center;
  font-size: 3rem;
}
.not-found {
  padding: 3rem;
}
</style>
