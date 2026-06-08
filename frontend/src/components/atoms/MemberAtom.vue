<script setup lang="ts">
import ExternalLinkAtom from "./ExternalLinkAtom.vue"
import ImageAtom from "./ImageAtom.vue"
const props = defineProps<{
  name: string
  role?: string
  orcid?: string
}>()
</script>

<template>
  <div class="card">
    <div class="name">
      <span>{{ props.name }}</span>
      <ExternalLinkAtom v-if="props.orcid" :href="props.orcid">
        <ImageAtom
          :src="'/img/orcid_badge.svg'"
          :width="'1em'"
          :container-padding="'0'"
          style="display: inline-block; margin-right: 4px"
        />
      </ExternalLinkAtom>
    </div>
    <p class="role">{{ props.role }}</p>
  </div>
</template>

<style scoped>
.card {
  width: 270px;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: start;
  border-radius: 8px;
  box-shadow:
    rgba(0, 0, 0, 0.2) 0px 1px 3px 0px,
    rgba(0, 0, 0, 0.2) 0px 1px 2px -1px;
  padding: 20px 10px;
  position: relative;
}

.name span {
  font-weight: 600;
  font-size: 1.25rem;
  line-height: 1.75rem;
}

.role {
  position: absolute;
  bottom: 10px;
  text-align: center;
  font-style: italic;
  font-size: 0.9em;
}

.external-link {
  margin-left: 8px;
}
</style>
