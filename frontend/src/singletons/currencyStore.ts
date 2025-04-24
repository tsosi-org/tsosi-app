import { ref } from "vue"
import {
  type Currency,
  getCurrencies as getRefCurrencies,
} from "@/singletons/ref-data"

export const defaultCurrency: Currency = {
  id: "EUR",
  name: "Euro",
}

/**
 * Special Currency object to represent selecting the original currency of an
 * object.
 */
export const originalCurrency = {
  id: "_original",
  name: "Original currency",
}

export const selectedCurrency = ref(defaultCurrency)

/**
 * The the global selected currency to the given code.
 * @param currencyCode The currency code
 */
export async function setSelectedCurrency(currencyCode: string): Promise<void> {
  const availableCurrencies = await getCurrencies()
  if (!availableCurrencies) {
    return
  }
  if (!(currencyCode in availableCurrencies)) {
    console.error(`Unsupported currency: ${currencyCode}`)
    return
  }
  selectedCurrency.value = availableCurrencies[currencyCode]
  console.log(`Currency change :${currencyCode}`)
}

export async function getCurrencies() {
  const availableCurrencies = { ...(await getRefCurrencies()) }
  availableCurrencies[originalCurrency.id] = originalCurrency
  return availableCurrencies
}
