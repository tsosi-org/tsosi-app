<script setup lang="ts">
import { changeTitle } from "@/utils/dom-utils"

export interface StaticContentComponentProps {
  title: string
}
const props = defineProps<StaticContentComponentProps>()

changeTitle(props.title)
</script>

<template>
  <div class="container small">
    <div class="regular-content static-content">
      <h1 class="page-title">{{ props.title }}</h1>
      <slot> My static content </slot>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 2.5rem;
  text-align: center;
  padding-top: 0;
}
</style>
