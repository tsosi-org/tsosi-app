<script setup lang="ts">
import NewsSubButtonAtom from "@/components/atoms/NewsSubButtonAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Newsletter">
    <NewsSubButtonAtom action="unsubscribe" />
  </StaticContentComponent>
</template>
