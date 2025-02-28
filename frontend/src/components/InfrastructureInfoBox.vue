<script setup lang="ts">
import { type InfrastructureDetails } from "@/singletons/ref-data"

const props = defineProps<{ details: InfrastructureDetails }>()
</script>

<template>
  <div clas="info-box infrastructure"></div>
</template>

<style lang="css" scoped>
.info-box {
  border: 2px solid;
  border-color: var(--p-primary);
  border-radius: 5px;
}
</style>
