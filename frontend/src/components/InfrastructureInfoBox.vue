<script setup lang="ts">
import { type EntityDetails } from "@/singletons/ref-data"
import InfoButtonAtom from "./atoms/InfoButtonAtom.vue"
import { RouterLink } from "vue-router"
import { formatDateWithPrecision } from "@/utils/data-utils"
import Panel from "primevue/panel"

const props = defineProps<{
  data: EntityDetails
  fullWidth?: boolean
  breakdownDisclaimer?: boolean
}>()
console.log(`Full width: ${props.fullWidth}`)
</script>

<template>
  <Panel
    v-if="props.data.infrastructure"
    toggleable
    class="info-box"
    :dt="{ border: 'inherit', borderRadius: 'inherit' }"
  >
    <template #header>
      <h2 class="info-box-header">Data perimeter</h2>
    </template>
    <div class="info-item">
      <h3>
        <span>Disclosed amounts</span>
        <InfoButtonAtom
          v-if="props.data.infrastructure.hide_amount"
          style="margin-left: 0.5em"
        >
          <template #popup>
            The individual funding amounts are not disclosed,
            <RouterLink to="/faq#partner-definition">see our FAQ</RouterLink>
          </template>
        </InfoButtonAtom>
      </h3>
      <span v-if="props.data.infrastructure.hide_amount">
        The transfer amounts are hidden.
      </span>
      <span v-else> The transfer amounts are displayed. </span>
    </div>

    <div v-if="props.data.infrastructure.date_data_update" class="info-item">
      <h3>Last data update</h3>
      <span>
        {{
          formatDateWithPrecision(
            props.data.infrastructure.date_data_update,
            "day",
          )
        }}
      </span>
    </div>
    <div v-if="props.breakdownDisclaimer" class="info-item">
      <h3>Supporter breakdown</h3>
      <span>
        The data does not include the supporters breakdown before 2021, but only
        the intermediary like a library consortia,
        <RouterLink to="/faq#partner-definition"> see more in FAQ </RouterLink>.
      </span>
    </div>
  </Panel>
</template>
