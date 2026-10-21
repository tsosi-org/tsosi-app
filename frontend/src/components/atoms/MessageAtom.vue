<script setup lang="ts">
import Message from "primevue/message"

/**
 * PrimeVue message with an icon showing its severity: messages have a
 * neutral frame, with no color (see the preset in `main.ts`).
 * Other attributes and events (`closable`, `@close`...) are passed to the
 * PrimeVue component.
 */
type Severity = "info" | "success" | "warn" | "error"

const props = withDefaults(defineProps<{ severity?: Severity }>(), {
  severity: "info",
})

const icons: Record<Severity, string> = {
  info: "circle-info",
  success: "circle-check",
  warn: "triangle-exclamation",
  error: "circle-exclamation",
}
</script>

<template>
  <Message :severity="props.severity">
    <template #icon>
      <font-awesome-icon
        :icon="['fas', icons[props.severity]]"
        class="message-icon"
        :class="props.severity"
      />
    </template>
    <slot></slot>
  </Message>
</template>

<style scoped>
.message-icon {
  flex-shrink: 0;
  font-size: 1.1rem;
  align-self: flex-start;
  margin-top: 0.15rem;
}

.message-icon.info {
  color: var(--p-primary-color);
}

.message-icon.success {
  color: var(--p-green-600);
}

.message-icon.warn {
  color: var(--p-yellow-600);
}

.message-icon.error {
  color: var(--p-red-600);
}
</style>
