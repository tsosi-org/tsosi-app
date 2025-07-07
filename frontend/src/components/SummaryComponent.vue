<script setup lang="ts">
import {
  type DataFieldProps,
  getItemLabel,
  getItemLink,
  formatValue,
} from "@/utils/data-utils"
import { RouterLink } from "vue-router"
import Country from "@/components/atoms/CountryAtom.vue"
import InfoButtonAtom from "./atoms/InfoButtonAtom.vue"
import { nullValues } from "@/utils/data-utils"
import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"
import EntityLinkDataAtom from "./atoms/EntityLinkDataAtom.vue"

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
      <div
        v-if="
          !nullValues.includes(getItemLabel(props.data, field)) ||
          field.type == 'boolean'
        "
        class="summary-field"
      >
        <div class="summary-label">
          {{ field.title
          }}<InfoButtonAtom v-if="field.info" :content="field.info" />&nbsp;:
        </div>
        <div class="summary-value">
          <EntityLinkDataAtom
            v-if="field.type == 'entityLink'"
            :data="props.data"
            :data-field="field"
          />
          <RouterLink
            v-else-if="field.type == 'pageLink'"
            :to="getItemLink(props.data, field.fieldLink)"
          >
            {{ getItemLabel(props.data, field) }}
          </RouterLink>

          <ExternalLinkAtom
            v-else-if="field.type == 'externalLink'"
            :href="getItemLink(props.data, field.fieldLink)"
            :label="getItemLabel(props.data, field)"
          />

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

          <div v-else-if="field.type == 'boolean'">
            <font-awesome-icon
              v-if="getItemLabel(props.data, field)"
              :icon="['fas', 'square-check']"
            />
            <font-awesome-icon v-else :icon="['fas', 'square-xmark']" />
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
  padding: 1em;

  &.info-box {
    border: 2px solid orange;
    border-radius: 5px;
  }
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
  flex: 0 0 min(35%, 150px);
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
