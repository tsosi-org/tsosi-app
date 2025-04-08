<script setup lang="ts">
const props = defineProps<{
  href: string
  label?: string
  rel?: string
  target?: string
}>()
</script>

<template>
  <a
    class="external-link"
    :href="props.href"
    :rel="props.rel || 'noopener noreferrer'"
    :target="props.target || '_blank'"
  >
    <slot>
      {{ props.label }}
    </slot>
  </a>
</template>
