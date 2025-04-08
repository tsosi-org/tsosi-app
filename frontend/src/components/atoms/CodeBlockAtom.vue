<script setup lang="ts">
const props = defineProps<{
  content?: string
  inline?: boolean
  background?: boolean
}>()
</script>

<template>
  <div
    class="code-block"
    :class="{ inline: props.inline, background: props.background }"
  >
    <slot>
      {{ props.content }}
    </slot>
  </div>
</template>

<style scoped>
.code-block {
  font-family: monospace;
  display: block;
  padding: 0 4px;
  white-space: pre;
  border-radius: 4px;
  overflow-x: scroll;

  &.inline {
    display: inline-block;
    width: fit-content;
    overflow-x: unset;
  }

  &.background {
    background-color: var(--p-neutral-200);
  }
}
</style>
