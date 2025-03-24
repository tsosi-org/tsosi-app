<script setup lang="ts">
import { RouterLink } from "vue-router"
import InfrastructureList from "@/components/atoms/InfrastructureList.vue"
</script>

<template>
  <div>
    Partner infrastructures:
    <InfrastructureList />
    <RouterLink to="/pages/faq#partner-definition">See our FAQ</RouterLink>
    to know more about partner infrastructures.
  </div>
</template>
