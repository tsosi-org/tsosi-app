<script setup lang="ts">
import { ref } from "vue"

interface StaticSectionProps {
  id?: string
  titleTag?: "h1" | "h2"
  titleClasses?: string[]
  noLink?: boolean
  title: string
  content?: string
}

const copied = ref(false)
const props = defineProps<StaticSectionProps>()

function copyFragmentLink() {
  const baseHref = window.location.href.split("#")[0]
  navigator.clipboard.writeText(`${baseHref}#${props.id}`)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>

<template>
  <div class="static-section" :id="props.id">
    <div class="section-header">
      <h2
        v-if="!props.titleTag || props.titleTag == 'h2'"
        class="section-title"
      >
        {{ props.title.split(" ").slice(0, -1).join(" ") }}
        <span style="white-space: nowrap">
          {{ props.title.split(" ").slice(-1)[0] }}
          <a
            v-if="props.id && !props.noLink"
            :href="`#${props.id}`"
            @click="copyFragmentLink"
            class="section-link"
          >
            <font-awesome-icon :icon="['fas', 'link']" />
          </a>
        </span>
        <span v-if="copied" class="copy-indicator" style="margin-left: 2px">
          Copied
          <font-awesome-icon
            :icon="['fas', 'check']"
            style="margin-left: 5px"
          />
        </span>
      </h2>
      <h1 v-else class="section-title">
        {{ props.title }}
        <a
          v-if="props.id && !props.noLink"
          :href="`#${props.id}`"
          @click="copyFragmentLink"
        >
          <font-awesome-icon :icon="['fas', 'link']" />
        </a>
        <span v-if="copied" class="copy-indicator">
          Copied
          <font-awesome-icon
            :icon="['fas', 'check']"
            style="margin-left: 5px"
          />
        </span>
      </h1>
    </div>

    <div>
      <slot>
        {{ props.content }}
      </slot>
    </div>
  </div>
</template>

<style scoped>
.static-section.targeted {
  & .section-header {
    background-color: var(--p-primary-50) !important;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    padding-left: 5px;
  }
}

.section-header {
  background-color: var(--color-background);
  position: sticky;
  top: var(--header-height);
  z-index: 2000;
}

.section-link {
  margin: 0 0.5em;
  font-size: 0.8em;
  color: var(--p-neutral-500);

  &:hover,
  &:focus {
    color: var(--color-heading);
  }
}

.copy-indicator {
  font-size: 1rem;
  color: var(--p-neutral-500);
}
</style>
