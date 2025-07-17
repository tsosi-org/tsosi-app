<script setup lang="ts">
import ProgressSpinner from "primevue/progressspinner"


const props = defineProps<{ width?: string }>()
const width = props.width || "50px"
</script>

<template>
  <div class="loader-container">
    <ProgressSpinner class="loader" stroke-width="1" />
  </div>
</template>

<style scoped>
.loader-container {
  position: absolute;
  left: 0;
  right: 0;
  width: 100%;
  height: 100%;
  display: flex;
  place-items: center;
  place-content: center;
  /* background-color: var(--c-white-mute) */
}

.loader {
  font-size: v-bind("width");
  width: 1em;
  height: 1em;
  display: inline-block;
}
</style>
