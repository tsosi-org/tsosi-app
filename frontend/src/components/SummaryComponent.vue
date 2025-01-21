<script setup lang="ts">
import {
  type DataFieldProps,
  getItemLabel,
  getItemLink,
  formatValue,
} from "@/utils/data-utils"
import { RouterLink } from "vue-router"
import Country from "@/components/atoms/CountryAtom.vue"

export interface SummaryProps {
  data: Record<string, any>
  fields: Array<DataFieldProps>
  explicit?: boolean
}

const props = defineProps<SummaryProps>()
</script>

<template>
  <div class="summary">
    <template v-for="field of props.fields" :key="field.id">
      <div v-if="getItemLabel(props.data, field)" class="summary-field">
        <div class="summary-label">{{ field.title }}:</div>
        <div class="summary-value">
          <RouterLink
            v-if="field.type == 'pageLink'"
            :to="getItemLink(props.data, field.fieldLink)"
          >
            {{ getItemLabel(props.data, field) }}
          </RouterLink>

          <a
            v-else-if="field.type == 'externalLink'"
            :href="getItemLink(props.data, field.fieldLink)"
          >
            {{ getItemLabel(props.data, field) }}
          </a>

          <Country
            v-else-if="field.type == 'country'"
            :code="getItemLabel(props.data, field)"
          />

          <div v-else-if="field.type == 'json'" class="data-json">
            {{ JSON.stringify(getItemLabel(props.data, field), null, 4) }}
          </div>

          <div v-else-if="props.explicit && field.type == 'dateWithPrecision'">
            {{ formatValue(getItemLabel(props.data, field).value, "date") }}
            <span class="date-precision">{{
              getItemLabel(props.data, field)?.precision
            }}</span>
            precision
          </div>

          <div v-else>
            {{ formatValue(getItemLabel(props.data, field), field.type) }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.summary {
  display: flex;
  flex-direction: column;
  gap: 1em;
  overflow-x: auto;
}

.summary-field {
  display: flex;
  flex-direction: row;
  gap: 1em;
}

.summary-value {
  display: contents;
}

.summary-label {
  color: var(--p-primary-800);
  font-weight: 700;
  flex: 0 0 min(50%, 150px);
  text-align: right;
}

.date-precision {
  font-style: italic;
  color: var(--p-neutral-600);
  font-weight: 500;
}

.data-json {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
