<script setup lang="ts">
import { getCountryIcon, getCountryLabel } from "@/utils/data-utils"

interface CountryProps {
  code?: string | null
}

const props = defineProps<CountryProps>()
</script>

<template>
  <div v-if="props.code" class="country-container">
    <img
      class="country-icon"
      :src="getCountryIcon(props.code)"
      :title="props.code"
    />
    {{ getCountryLabel(props.code) }}
  </div>
</template>

<style scoped>
.country-container {
  display: inline-flex;
  flex-direction: row;
  gap: 0.5em;
}

.country-icon {
  width: 25px;
  border-radius: 3px;
}
</style>
