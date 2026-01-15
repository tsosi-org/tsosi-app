<script setup lang="ts">
import { onBeforeMount, ref, type Ref } from "vue"

import ImageAtom from "./ImageAtom.vue"

import type { Entity } from "@/singletons/ref-data"
import { type DataFieldProps, getItemValue } from "@/utils/data-utils"
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
  <div class="container">
  <RouterLink
    v-if="entity"
    class="entity-link"
    :class="{ icon: entity?.icon != null }"
    :to="getEntityUrl(entity)"
    :title="entity.name"
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
  <span v-if="entity && props.dataField.field == 'emitter' && props.data.emitter_sub" class="entity-label-detail">{{ `(${props.data.emitter_sub})` }}</span>
  </div>
</template>

<style scoped>
.container {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: left;
  justify-content: left;
  margin: 0;
}

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

.entity-label-detail {
  margin-left: 0.2em;
}
</style>
