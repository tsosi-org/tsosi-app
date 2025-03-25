<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"

export interface EmailAtomProps {
  user: string
  domain: string
  asMailTo?: boolean
}

onBeforeMount(async () => {
  await new Promise((r) => setTimeout(r, 400))
  loaded.value = true
})
const loaded = ref(false)
const props = defineProps<EmailAtomProps>()

const email = computed(() => {
  if (!loaded.value) {
    return ""
  }
  return `${props.user}@${props.domain}`
})
</script>

<template>
  <a v-if="props.asMailTo" :href="`mailto:${email}`">
    {{ email }}
  </a>
  <span v-else>
    {{ email }}
  </span>
</template>
