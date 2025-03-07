<script setup lang="ts">
import { type EntityDetails } from "@/singletons/ref-data"
import InfoButtonAtom from "./atoms/InfoButtonAtom.vue"
import { RouterLink } from "vue-router"
import { formatDateWithPrecision } from "@/utils/data-utils"

const props = defineProps<{
  data: EntityDetails
  fullWidth?: boolean
  breakdownDisclaimer?: boolean
}>()
console.log(`Full width: ${props.fullWidth}`)
</script>

<template>
  <section
    v-if="props.data.infrastructure"
    class="info-box infrastructure"
    :class="{ expand: props.fullWidth }"
  >
    <div v-if="props.data.date_inception" class="info-item">
      <h3>Inception date</h3>
      <span>
        {{ props.data.date_inception.getFullYear() }}
      </span>
    </div>
    <div
      v-if="
        props.data.infrastructure.date_data_start &&
        props.data.infrastructure.date_data_end
      "
      class="info-item"
    >
      <h3>Data coverage</h3>
      <span>
        {{ props.data.infrastructure.date_data_start.getFullYear() }} to
        {{ props.data.infrastructure.date_data_end.getFullYear() }}
      </span>
    </div>

    <div class="info-item">
      <h3>
        <span>Disclosed amounts</span>
        <InfoButtonAtom
          v-if="props.data.infrastructure.hide_amount"
          style="margin-left: 0.5em"
        >
          <template #default>
            The individual funding amounts are not disclosed,
            <RouterLink to="/faq#partner-definition">see our FAQ</RouterLink>
          </template>
        </InfoButtonAtom>
      </h3>
      <span v-if="props.data.infrastructure.hide_amount">
        The transfert amounts are hidden.
      </span>
      <span v-else> The transfert amounts are displayed. </span>
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
  </section>
</template>
