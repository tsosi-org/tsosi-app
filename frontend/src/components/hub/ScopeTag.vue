<script setup lang="ts">
import Tag from "primevue/tag"

import {
  SCOPE_INFOS,
  SCOPE_LABELS,
  SCOPE_SEVERITIES,
} from "@/singletons/hub-organizations"
import type { EntityScope } from "@/singletons/ref-data"

/**
 * The scope of a beneficiary whose supports aren't public, explained by its
 * tooltip. Nothing for a beneficiary in scope.
 */
const props = defineProps<{ scope: EntityScope }>()
</script>

<template>
  <Tag
    v-if="props.scope != 'in_scope'"
    v-tooltip.bottom="SCOPE_INFOS[props.scope]"
    class="scope-tag"
    :severity="SCOPE_SEVERITIES[props.scope]"
    :value="SCOPE_LABELS[props.scope]"
  />
</template>

<style scoped>
.scope-tag {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
