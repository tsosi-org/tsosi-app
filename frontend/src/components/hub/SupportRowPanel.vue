<script setup lang="ts">
import Message from "@/components/atoms/MessageAtom.vue"
import NewOrganizationPanel from "@/components/hub/NewOrganizationPanel.vue"
import SupportDates from "@/components/hub/SupportDates.vue"
import type {
  DateFieldName,
  DeclarationErrors,
} from "@/singletons/hub-declarations"
import type { Entity } from "@/singletons/ref-data"

/**
 * The panel under the row being edited: its dates, when the Date cell is
 * open, the organization being added from its name, and the errors of the
 * row, or a notice.
 */
const props = defineProps<{
  organizationId: string
  showDates: boolean
  errors: DeclarationErrors
  // The messages of `errors`, and those of the cells
  errorMessages: string[]
  // The name of the organization being added, if any
  addingName: string | null
  notice?: string | null
}>()
const dates = defineModel<Record<DateFieldName, string>>("dates", {
  required: true,
})
const emit = defineEmits<{
  added: [entity: Entity]
  cancelAdd: []
}>()
</script>

<template>
  <div class="support-row-panel">
    <SupportDates
      v-if="props.showDates"
      v-model:dates="dates"
      :errors="props.errors"
    />
    <NewOrganizationPanel
      v-if="props.addingName != null"
      :organizationId="props.organizationId"
      :initialName="props.addingName"
      @added="(entity) => emit('added', entity)"
      @cancel="emit('cancelAdd')"
    />
    <Message v-if="props.notice && !props.errorMessages.length" severity="warn">
      {{ props.notice }}
    </Message>
    <Message v-if="props.errorMessages.length" severity="error">
      <p v-if="props.errorMessages.length == 1" class="errors">
        {{ props.errorMessages[0] }}
      </p>
      <ul v-else class="errors">
        <li v-for="message of props.errorMessages" :key="message">
          {{ message }}
        </li>
      </ul>
    </Message>
  </div>
</template>

<style scoped>
.support-row-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-width: 60rem;
  color: var(--p-text-color);
}

.errors {
  margin: 0;
}

ul.errors {
  padding-left: 1.2rem;
}
</style>
