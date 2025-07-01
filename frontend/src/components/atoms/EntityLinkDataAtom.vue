<script setup lang="ts">
import { type DataFieldProps, getItemValue } from "@/utils/data-utils"
import ImageAtom from "./ImageAtom.vue"
import { onBeforeMount, ref, type Ref } from "vue"
import type { Entity } from "@/singletons/ref-data"
import { getEntityUrl } from "@/utils/url-utils"

const props = defineProps<{
  data: Record<string, any>
  dataField: DataFieldProps
}>()

const entity: Ref<Entity | undefined> = ref()

onBeforeMount(() => {
  const entityFromData = getItemValue(props.data, props.dataField) as
    | Entity
    | undefined
  if (!entityFromData) {
    return
  }
  entity.value = entityFromData
})
</script>

<template>
  <RouterLink
    v-if="entity"
    class="entity-link"
    :class="{ icon: entity?.icon != null }"
    :to="getEntityUrl(entity)"
  >
    <ImageAtom
      class="entity-icon"
      v-if="entity.icon"
      :src="entity.icon"
      :width="'1.4em'"
      :height="'1.4em'"
      :container-padding="'0px'"
    />
    <span class="entity-label">
      {{ entity.short_name || entity.name }}
    </span>
  </RouterLink>
</template>

<style scoped>
.entity-link {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5em;

  &.icon {
    white-space: nowrap;
  }
}
</style>
