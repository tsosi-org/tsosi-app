<script setup lang="ts">
import { getInfrastructures } from "@/singletons/ref-data"
import { RouterLink } from "vue-router"
import { getEntityUrl } from "@/utils/url-utils"

const infras = getInfrastructures()
</script>

<template>
  <ul>
    <li v-for="infra of infras" :key="infra.id">
      <RouterLink :to="getEntityUrl(infra.id)">
        {{ infra.name }}
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.ul {
  list-style: none;
  padding: 5px;
  position: relative;
}
</style>
