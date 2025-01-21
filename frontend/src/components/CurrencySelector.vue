<script setup lang="ts">
import { ref, type Ref, onMounted, watchEffect } from "vue"
import {
  selectedCurrency,
  setSelectedCurrency,
  getCurrencies,
} from "@/singletons/currencyStore"
import { type Currency, type DeepReadonly } from "@/singletons/ref-data"
import Select from "primevue/select"

const currency = ref(selectedCurrency.value)
const availableCurrencies: Ref<Array<DeepReadonly<Currency>>> = ref([])

onMounted(async () => {
  const currencies = await getCurrencies()
  if (currencies != null) {
    availableCurrencies.value = Object.values(currencies)
  }
})

watchEffect(() => {
  if (currency.value == null || currency.value == selectedCurrency.value) {
    return
  }
  setSelectedCurrency(currency.value.id)
})
</script>

<template>
  <Select
    v-model="currency"
    :options="availableCurrencies"
    optionLabel="name"
  />
</template>
