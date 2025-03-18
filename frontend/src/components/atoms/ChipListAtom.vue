<script setup lang="ts">
import Chip from "primevue/chip"

export interface ChipConfig {
  label: string
  icon?: string
  iconText?: string
  link?: string
}

const props = defineProps<{
  tags: ChipConfig[]
  chipYGap?: string
  center?: boolean
}>()
</script>

<template>
  <div
    v-if="props.tags.length"
    class="icon-label-list"
    :class="{ center: props.center }"
  >
    <div v-for="(iconLabel, index) of props.tags" :key="index">
      <a
        v-if="iconLabel.link"
        :href="iconLabel.link"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Chip
          class="chip-link"
          :label="iconLabel.label"
          :dt="{
            gap: '0.8em',
            fontSize: '0.9rem',
            padding: { y: chipYGap ?? '0.25rem', x: '1rem' },
          }"
          pt:root:class="chip-link"
          pt:label:class="chip-link-label"
        >
          <template #icon>
            <div class="chip-icon-group">
              <font-awesome-icon
                v-if="iconLabel.icon"
                class="icon"
                :icon="iconLabel.icon"
              />
              <span v-if="iconLabel.iconText">{{ iconLabel.iconText }}</span>
            </div>
          </template>
        </Chip>
      </a>
      <Chip
        v-else
        :label="iconLabel.label"
        :dt="{
          gap: '0.8em',
          fontSize: '0.9rem',
          padding: { y: chipYGap ?? '0.25rem', x: '1rem' },
        }"
      >
        <template #icon>
          <div class="chip-icon-group">
            <font-awesome-icon
              v-if="iconLabel.icon"
              class="icon"
              :icon="iconLabel.icon"
            />
            <span v-if="iconLabel.iconText">{{ iconLabel.iconText }}</span>
          </div>
        </template>
      </Chip>
    </div>
  </div>
</template>

<style scoped>
.icon-label-list {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  row-gap: 1em;
  column-gap: 2em;

  &.center {
    justify-content: center;
  }
}

.chip-icon-group {
  display: inline-flex;
  gap: 0.5em;
  align-items: center;
}
</style>
