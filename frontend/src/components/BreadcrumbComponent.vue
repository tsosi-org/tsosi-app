<script setup lang="ts">
import { RouterLink } from "vue-router"

export interface BreadcrumbItem {
  label: string
  icon?: string
  route: string
}

const props = defineProps<{ items: Array<BreadcrumbItem> }>()
</script>

<template>
  <nav class="breadcrumb">
    <ol class="breadcrumb-list">
      <template v-for="(item, index) of props.items" :key="index">
        <li class="breadcrumb-item">
          <font-awesome-icon
            v-if="item.icon"
            class="breadcrumb-icon"
            :icon="item.icon"
          />
          <RouterLink v-if="item.route" :to="item.route">
            {{ item.label }}
          </RouterLink>
        </li>
        <li v-if="index != props.items.length - 1" class="breadcrumb-separator">
          <font-awesome-icon icon="angle-right" />
        </li>
      </template>
    </ol>
  </nav>
</template>

<style scoped>
.breadcrumb {
  padding: 1rem;
  overflow-x: auto;
}

.breadcrumb-list {
  margin: 0;
  padding: 0;
  list-style-type: none;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 0.5rem;
}

.breadcrumb-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5em;
}

.breadcrumb-separator {
  font-size: 14px;
  display: flex;
  align-items: center;
  color: var(--p-primary-300);
}

.breadcrumb-icon {
  color: var(--p-primary-900);
}
</style>
