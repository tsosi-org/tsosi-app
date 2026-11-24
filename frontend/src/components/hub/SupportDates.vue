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
 * five dates of the data collection schema, in two groups, the payment and
 * the agreement period. At least one of them is required: a payment date or
 * the agreement period. The invalid ones are flagged; the panel lists the
 * errors. Opened, the focus is on the first one, the invoice date.
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

const groups: {
  id: string
  title: string
  requirement: string
  fields: DateFieldName[]
}[] = [
  {
    id: "payment",
    title: "Payment date",
    requirement: "(At least one)",
    fields: ["date_invoice", "date_payment_emitter", "date_payment_recipient"],
  },
  {
    id: "agreement",
    title: "Agreement period",
    requirement: "(Optional, if multiple years are covered)",
    fields: ["date_start", "date_end"],
  },
]

// Shown on the label's hover
const dateInfos: Partial<Record<DateFieldName, string>> = {
  date_payment_emitter: "Paid by your organization",
  date_payment_recipient: "Received by the beneficiary",
}

function dateInvalid(field: DateFieldName): boolean {
  const text = dates.value[field].trim()
  return !!props.errors[field] || (text != "" && parseDateInput(text) == null)
}
</script>

<template>
  <div ref="root" class="support-dates">
    <div class="date-groups">
      <fieldset
        v-for="group of groups"
        :key="group.id"
        :class="['date-group', `date-group-${group.id}`]"
      >
        <legend>
          <span class="group-title">{{ group.title }}</span>
          <span class="group-requirement">{{ group.requirement }}</span>
        </legend>
        <div class="date-fields">
          <div v-for="field of group.fields" :key="field" class="field">
            <label
              v-tooltip.bottom="dateInfos[field]"
              :for="`${idPrefix}-${field}`"
            >
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
      </fieldset>
    </div>
  </div>
</template>

<style scoped>
/* The text color of the table's column titles and of the inputs */
.support-dates {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  color: var(--p-text-color);
  max-width: 60rem;
}

.date-format {
  margin: 0;
  color: var(--p-text-muted-color);
}

.date-groups {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 2rem;
}

.date-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: none;

  & legend {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding: 0;
    gap: 0.7rem;
    margin-bottom: 0.5rem;
  }
}

.group-title {
  font-weight: 600;
}

.group-requirement {
  color: var(--p-text-muted-color);
  font-size: var(--text-xs);
}

.date-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 10.5rem;

  & label {
    align-self: flex-start;
  }
}
</style>
