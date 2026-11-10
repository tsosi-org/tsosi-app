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
  /* Card style of base.css, without hover */
  background-color: white;
  border: var(--card-border);
  border-radius: var(--card-radius);
  overflow: hidden;
  padding: 20px 10px;
  position: relative;
}

.name span {
  font-weight: 600;
  font-size: var(--text-md);
  line-height: 1.75rem;
}

.role {
  position: absolute;
  bottom: 10px;
  text-align: center;
  font-size: var(--text-xs);
}

.external-link {
  margin-left: 8px;
}
</style>
