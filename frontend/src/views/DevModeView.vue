<script setup lang="ts">
import { devMode } from "@/singletons/devMode"
import { onBeforeMount } from "vue"

import { useRouter } from "vue-router"

onBeforeMount(() => {
  devMode.value = true
  const router = useRouter()
  router.push({ name: "home" })
})
</script>

<template></template>

<style scoped></style>
