<script setup lang="ts">
import type { Entity } from "@/singletons/ref-data"
import Image from "./atoms/ImageAtom.vue"
import { RouterLink } from "vue-router"
import { getEntityUrl } from "@/utils/url-utils"
export interface EntityMapSummaryProps {
  entity: Entity
  forceImage?: boolean
}

const props = defineProps<EntityMapSummaryProps>()
</script>

<template>
  <div class="wrapper">
    <div class="content">
      <Image
        v-if="props.forceImage || props.entity.logo"
        :src="props.entity.logo"
        :height="'100px'"
        :width="'100px'"
        :center="true"
      />
      <h2>
        <RouterLink :to="getEntityUrl(props.entity.id)">
          {{ props.entity.name }}
        </RouterLink>
      </h2>
    </div>
    <div class="controls"></div>
  </div>
</template>

<style scoped>
.wrapper {
  position: relative;
  padding: 2px;
}

.content {
  display: flex;
  place-items: center;
  gap: 1em;
  position: relative;
}
</style>
