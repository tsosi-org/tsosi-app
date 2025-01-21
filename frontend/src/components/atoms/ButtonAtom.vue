<script setup lang="ts">
import Button from "primevue/button"
import { type LinkConfig, getItemLink } from "@/utils/data-utils"

export type ButtonType = "pageLink" | "externalLink"
export interface ButtonProps {
  id: string
  label?: string
  icon?: string
  type: ButtonType
  linkConfig?: LinkConfig
  data?: Record<string, any>
  severity?: string
}

const props = defineProps<ButtonProps>()
</script>

<template>
  <Button
    v-if="props.type == 'pageLink'"
    as="router-link"
    :label="props.label"
    :to="getItemLink(props.data, props.linkConfig)"
    :severity="props.severity"
  >
    <template #icon v-if="props.icon">
      <font-awesome-icon :icon="props.icon" />
    </template>
  </Button>

  <Button
    v-if="props.type == 'externalLink'"
    as="link"
    :label="props.label"
    :to="getItemLink(props.data, props.linkConfig)"
    :severity="props.severity"
  >
    <template #icon v-if="props.icon">
      <font-awesome-icon :icon="props.icon" />
    </template>
  </Button>
</template>
