<script setup lang="ts">
import EntityTitleLogo from "@/components/EntityTitleLogo.vue"
import type { Entity } from "@/singletons/ref-data"

export interface CountryEntityListProps {
  title?: string
  entities: Entity[]
}

const props = defineProps<CountryEntityListProps>()
</script>

<template>
  <div class="country-list">
    <h3 v-if="props.title" class="country-list-title">{{ props.title }}</h3>
    <div class="entity-list">
      <EntityTitleLogo
        v-for="entity of props.entities"
        :entity="entity"
        :key="entity.id"
        :force-image="props.entities.length > 1"
      />
    </div>
  </div>
</template>

<style scoped>
.country-list {
  font-size: var(--font-size);
  position: relative;
}

.country-list-title {
  padding: 5px;
  background-color: #eee;
  border-radius: 5px;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--p-text-color);
  text-align: center;
}

.entity-list {
  padding: 10px 5px;
}

.entity-list > * {
  margin-bottom: 2px;
  &::after {
    content: "";
    position: absolute;
    margin-top: 2px;
    margin-left: 25%;
    width: 50%;
    bottom: -2px;
    height: 1px;
    background-color: #cccccc;
  }
}

.entity-list > *:last-child {
  margin-bottom: unset;
  &::after {
    content: unset;
    height: unset;
  }
}
</style>
