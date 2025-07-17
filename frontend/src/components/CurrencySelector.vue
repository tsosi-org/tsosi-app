<script setup lang="ts">
import { ref, type Ref, onMounted, watch } from "vue"
import Select from "primevue/select"

import {
  selectedCurrency,
  setSelectedCurrency,
  getCurrencies,
} from "@/singletons/currencyStore"
import { type Currency, type DeepReadonly } from "@/singletons/ref-data"


const currency = ref(selectedCurrency.value)
const availableCurrencies: Ref<Array<DeepReadonly<Currency>>> = ref([])

onMounted(async () => {
  const currencies = await getCurrencies()
  if (currencies != null) {
    availableCurrencies.value = Object.values(currencies)
  }
})

// If `currency` changes, only update the selected currency if it's a different
// value. The values can be the same when the change comes from an external
// source than this `currencySelector`.
watch(currency, () => {
  if (currency.value == null || currency.value == selectedCurrency.value) {
    return
  }
  setSelectedCurrency(currency.value.id)
})

// Always keep the currency model aligned with the selected currency.
watch(selectedCurrency, () => {
  if (currency.value == selectedCurrency.value) {
    return
  }
  currency.value = selectedCurrency.value
})
</script>

<template>
  <Select
    v-model="currency"
    :options="availableCurrencies"
    optionLabel="name"
  />
</template>
