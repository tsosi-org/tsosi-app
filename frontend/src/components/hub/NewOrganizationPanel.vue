<script setup lang="ts">
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import { ref, useId } from "vue"

import Message from "@/components/atoms/MessageAtom.vue"
import { addOrganization } from "@/singletons/hub-organizations"
import type { Entity } from "@/singletons/ref-data"

/**
 * Add an organization missing from TSOSI from its name, when it has no ROR
 * or Wikidata ID: those are typed in the search, which finds their record.
 */
const props = defineProps<{
  // The organization whose Hub it is
  organizationId: string
  // The name searched
  initialName: string
}>()
const emit = defineEmits<{
  added: [entity: Entity]
  cancel: []
}>()

const idPrefix = useId()
const name = ref(props.initialName)
const errors = ref<Record<string, string>>({})
const busy = ref(false)

async function add() {
  if (busy.value) {
    return
  }
  if (!name.value.trim()) {
    errors.value = { name: "Enter the organization's name." }
    return
  }
  busy.value = true
  errors.value = {}
  const result = await addOrganization(props.organizationId, {
    name: name.value.trim(),
  })
  busy.value = false
  if (result.error) {
    errors.value =
      result.status == 400 && result.data?.name
        ? { name: String(result.data.name) }
        : { detail: "The organization couldn't be added. Please try again." }
    return
  }
  emit("added", result.data as Entity)
}
</script>

<template>
  <form class="new-organization" @submit.prevent="add">
    <h4>Add a new organization</h4>
    <p class="explanation">
      If it has a ROR or Wikidata ID, type it in the search instead: TSOSI then
      gets its details from there.
    </p>
    <div class="field">
      <label :for="`${idPrefix}-name`">Name</label>
      <InputText
        :id="`${idPrefix}-name`"
        v-model="name"
        :invalid="!!errors.name"
        fluid
      />
      <small v-if="errors.name" class="error">{{ errors.name }}</small>
    </div>
    <Message v-if="errors.detail" severity="error">
      {{ errors.detail }}
    </Message>
    <div class="actions">
      <Button
        label="Cancel"
        severity="secondary"
        type="button"
        @click="emit('cancel')"
      />
      <Button label="Add this organization" type="submit" :loading="busy" />
    </div>
  </form>
</template>

<style scoped>
.new-organization {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--p-neutral-300);
  border-radius: 6px;
  background: var(--p-neutral-50);
}

h4 {
  margin: 0;
}

.explanation {
  margin: 0;
  color: var(--p-neutral-600);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;

  & label {
    font-weight: 600;
  }
}

.error {
  color: var(--p-red-600);
}

.actions {
  display: flex;
  gap: 0.5rem;
}
</style>
