<script setup lang="ts">
import { computed, onBeforeMount, ref, type Ref } from "vue"
import { RouterLink } from "vue-router"

import ImageAtom from "./ImageAtom.vue"

import type { Entity } from "@/singletons/ref-data"
import { type DataFieldProps, getItemValue } from "@/utils/data-utils"
import { getEntityUrl } from "@/utils/url-utils"

const props = defineProps<{
  data: Record<string, any>
  dataField: DataFieldProps
  // Show the entity without the link to its page
  noLink?: boolean
  hideIcon?: boolean
}>()

const entity: Ref<Entity | undefined> = ref()
// The Hub's entities that aren't on the public site have no page
const linked = computed(() => !props.noLink && entity.value?.is_public != false)

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
  <div class="entity-link-data">
    <component
      :is="linked ? RouterLink : 'span'"
      v-if="entity"
      class="entity-link"
      :class="{ icon: entity?.icon != null && !props.hideIcon }"
      :to="linked ? getEntityUrl(entity) : undefined"
      :title="entity.name"
    >
      <ImageAtom
        class="entity-icon"
        v-if="
          entity.icon && !props.hideIcon && props.dataField.field != 'sources'
        "
        :src="entity.icon"
        :width="'1.4em'"
        :height="'1.4em'"
        :container-padding="'0px'"
      />
      <span class="entity-label">
        {{ entity.short_name || entity.name }}
      </span>
    </component>
    <span
      v-if="
        entity && props.dataField.field == 'emitter' && props.data.emitter_sub
      "
      class="entity-label-detail"
      >{{ `(${props.data.emitter_sub})` }}</span
    >
  </div>
</template>

<style scoped>
.entity-link-data {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: left;
  margin: 0;
}

.entity-link {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5em;
  width: 100%;
  height: 100%;
  padding: 2px 4px;

  &.icon {
    white-space: nowrap;
  }
}

.entity-label-detail {
  margin-left: 0.2em;
}

.provider_icon {
  width: 1.4em;
  height: 1.4em;
  margin-left: 0.5em;
}
</style>
