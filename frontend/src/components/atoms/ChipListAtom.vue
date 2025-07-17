<script setup lang="ts">
import Chip from "primevue/chip"

import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"


export interface ChipConfig {
  label: string
  icon?: string[]
  iconText?: string
  link?: string
  info?: string
  showCallback?: () => any
}

const props = defineProps<{
  chips: ChipConfig[]
  chipYGap?: string
  center?: boolean
}>()
</script>

<template>
  <div
    v-if="props.chips.length"
    class="icon-label-list"
    :class="{ center: props.center }"
  >
    <div v-for="(chip, index) of props.chips" :key="index">
      <a
        v-if="chip.link"
        :href="chip.link"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Chip
          class="chip-link"
          :label="chip.label"
          :dt="{
            gap: '0.8rem',
            fontSize: '0.9rem',
            padding: { y: chipYGap ?? '0.25rem', x: '1rem' },
          }"
          pt:root:class="chip-link"
          pt:label:class="chip-link-label"
        >
          <template #icon>
            <div class="chip-icon-group">
              <font-awesome-icon
                v-if="chip.icon"
                class="icon"
                :icon="chip.icon"
              />
              <span v-if="chip.iconText">{{ chip.iconText }}</span>
            </div>
          </template>
        </Chip>
      </a>
      <InfoButtonAtom v-else-if="chip.info" :content="chip.info">
        <template #body>
          <Chip
            :label="chip.label"
            :dt="{
              gap: '0.8rem',
              fontSize: '0.9rem',
              padding: { y: chipYGap ?? '0.25rem', x: '1rem' },
            }"
          >
            <template #icon>
              <div class="chip-icon-group">
                <font-awesome-icon
                  v-if="chip.icon"
                  class="icon"
                  :icon="chip.icon"
                />
                <span v-if="chip.iconText">{{ chip.iconText }}</span>
              </div>
            </template>
          </Chip>
        </template>
      </InfoButtonAtom>
      <Chip
        v-else
        :label="chip.label"
        :dt="{
          gap: '0.8rem',
          fontSize: '0.9rem',
          padding: { y: chipYGap ?? '0.25rem', x: '1rem' },
        }"
      >
        <template #icon>
          <div class="chip-icon-group">
            <font-awesome-icon
              v-if="chip.icon"
              class="icon"
              :icon="chip.icon"
            />
            <span v-if="chip.iconText">{{ chip.iconText }}</span>
          </div>
        </template>
      </Chip>
    </div>
  </div>
</template>

<style scoped>
.icon-label-list {
  font-size: 1rem;
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  row-gap: 1rem;
  column-gap: 2rem;

  &.center {
    justify-content: center;
  }
}

.chip-icon-group {
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
}
</style>
