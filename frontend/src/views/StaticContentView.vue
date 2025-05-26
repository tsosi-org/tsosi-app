<script setup lang="ts">
import { changeMetaTitle } from "@/utils/dom-utils"

export interface StaticContentComponentProps {
  title: string
}
const props = defineProps<StaticContentComponentProps>()

changeMetaTitle(props.title)
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

.static-content {
  margin-bottom: 2rem;

  & :deep(h1),
  & :deep(h2),
  & :deep(h3),
  & :deep(h4),
  & :deep(h5),
  & :deep(h6) {
    margin: 1.5em 0 0.35em 0;
  }

  & h1.page-title {
    margin: 1em 0;
  }
}
</style>
