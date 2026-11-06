<script setup lang="ts">
import InputText from "primevue/inputtext"
import { onMounted, ref, useId } from "vue"

import {
  DATE_FIELDS,
  DATE_LABELS,
  parseDateInput,
  type DateFieldName,
  type DeclarationErrors,
} from "@/singletons/hub-declarations"

/**
 * The dates of the support being edited, in the panel under its row: the
 * five dates of the data collection schema. The invalid ones are flagged;
 * the panel lists the errors. Opened, the focus is on the first one, the
 * invoice date.
 */
const props = defineProps<{ errors: DeclarationErrors }>()
const dates = defineModel<Record<DateFieldName, string>>("dates", {
  required: true,
})

const idPrefix = useId()

const root = ref<HTMLElement | null>(null)

onMounted(() => {
  root.value
    ?.querySelector<HTMLInputElement>(
      `#${CSS.escape(`${idPrefix}-${DATE_FIELDS[0]}`)}`,
    )
    ?.focus()
})

const dateFormat = "A year (2024), a month (2024-03) or a day (2024-03-13)."
const requiredDate =
  "At least one of the invoice, sent, received or agreement start dates is required."
const agreement =
  "The period covered by the agreement, if there is one: both its start and end, or neither."
const dateInfos: Record<DateFieldName, string> = {
  date_invoice: `${dateFormat} ${requiredDate}`,
  date_payment_emitter: `Paid by the organization. ${dateFormat} ${requiredDate}`,
  date_payment_recipient: `Received by the beneficiary. ${dateFormat} ${requiredDate}`,
  date_start: `${agreement} ${dateFormat}`,
  date_end: `${agreement} ${dateFormat}`,
}

function dateInvalid(field: DateFieldName): boolean {
  const text = dates.value[field].trim()
  return !!props.errors[field] || (text != "" && parseDateInput(text) == null)
}
</script>

<template>
  <div ref="root" class="support-dates">
    <div class="date-fields">
      <div v-for="field of DATE_FIELDS" :key="field" class="field">
        <label :for="`${idPrefix}-${field}`">
          <span v-tooltip.bottom="dateInfos[field]" class="field-info">
            <font-awesome-icon :icon="['fas', 'circle-question']" />
          </span>
          {{ DATE_LABELS[field] }}
        </label>
        <InputText
          :id="`${idPrefix}-${field}`"
          v-model="dates[field]"
          placeholder="YYYY-MM-DD"
          :invalid="dateInvalid(field)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The text color of the table's column titles and of the inputs */
.support-dates {
  color: var(--p-text-color);
  max-width: 60rem;
}

.date-fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;

  & label {
    font-weight: 600;
  }
}

/* The same as the table's column titles */
.field-info {
  margin-right: 0.3em;
}
</style>
