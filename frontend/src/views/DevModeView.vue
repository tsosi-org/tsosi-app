<script setup lang="ts">
import { onBeforeMount } from "vue"
import { useRouter } from "vue-router"

import { devMode } from "@/singletons/devMode"

onBeforeMount(() => {
  devMode.value = true
  const router = useRouter()
  router.push({ name: "home" })
})
</script>

<template><div></div></template>

<style scoped></style>
