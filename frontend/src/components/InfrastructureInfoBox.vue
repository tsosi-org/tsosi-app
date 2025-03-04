<script setup lang="ts">
import { type InfrastructureDetails } from "@/singletons/ref-data"

const props = defineProps<{ details: InfrastructureDetails }>()
</script>

<template>
  <section clas="info-box infrastructure">
    <h2>Data coverage</h2>
    <div></div>
    <h2>Last update</h2>
    <div>{{ props.details }}</div>
  </section>
</template>

<style lang="css" scoped>
.info-box {
  border: 2px solid;
  border-color: var(--p-primary);
  border-radius: 5px;
}
</style>
