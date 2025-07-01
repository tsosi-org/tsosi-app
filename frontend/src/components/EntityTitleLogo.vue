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
      <span>
        <RouterLink :to="getEntityUrl(props.entity)">
          {{ props.entity.name }}
        </RouterLink>
      </span>
    </div>
    <div class="controls"></div>
  </div>
</template>

<style scoped>
.wrapper {
  font-size: var(--font-size);
  position: relative;
  padding: 2px;
}

.content {
  display: flex;
  place-items: center;
  gap: 1em;
  position: relative;
}

a {
  text-decoration: underline;
  color: initial;
}
</style>
