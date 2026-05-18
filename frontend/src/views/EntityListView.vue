<script lang="ts" setup>
import EntityCard from "@/components/EntityCard.vue"
import DataView from "primevue/dataview"
import Divider from "primevue/divider"
import MultiSelect from "primevue/multiselect"
import SelectButton from "primevue/selectbutton"
import ToggleButton from "primevue/togglebutton"
import {
  computed,
  onMounted,
  ref,
  watch,
  type DeepReadonly,
  type Ref,
} from "vue"
import { useRoute, useRouter } from "vue-router"

import { getCountries, getEntities, type Entity } from "@/singletons/ref-data"

const rowsPerPage = 64
const route = useRoute()
const router = useRouter()

type FilterValue = {
  name: string
  code: string
}

const allEntities: Ref<DeepReadonly<Entity[]>> = ref([])
const roleOptions: Ref<FilterValue[]> = ref([
  { name: "Open infrastructures", code: "recipient" },
  { name: "Supporters", code: "emitter" },
])
const selectedRole: Ref<string> = ref("recipient")
const countryOptions: Ref<FilterValue[]> = ref([])
const selectedCountries: Ref<FilterValue[]> = ref([])
const isPartner = ref(false)
const isSCOSS = ref(false)
const isPOSI = ref(false)
const isBarcelona = ref(false)
const currentPage = ref(1)
const isSyncingFromRoute = ref(false)

onMounted(async () => {
  const loadedEntities = (await getEntities()) || {}
  allEntities.value = Object.values(loadedEntities)
  const countries = (await getCountries()) || {}
  countryOptions.value = [
    ...new Set(Object.values(loadedEntities).map((entity) => entity.country)),
  ]
    .filter((country) => country != undefined)
    .map((country) => {
      return {
        name: countries[country]?.name,
        code: countries[country]?.code.toUpperCase(),
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
  applyQueryToFilters()
})

watch(
  () => route.query,
  () => {
    applyQueryToFilters()
  },
)

watch(
  [selectedRole, selectedCountries, isPartner, isSCOSS, isPOSI, isBarcelona],
  () => {
    if (isSyncingFromRoute.value) {
      return
    }
    syncFiltersToQuery()
  },
  { deep: true },
)

function normalizeQueryValue(value: unknown): string {
  if (typeof value === "string") {
    return value
  }
  if (Array.isArray(value)) {
    return typeof value[0] === "string" ? value[0] : ""
  }
  return ""
}

function parseCsvQuery(value: unknown): string[] {
  const normalized = normalizeQueryValue(value)
  if (!normalized) {
    return []
  }
  return normalized
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean)
}

function parseBooleanQuery(value: unknown): boolean {
  const normalized = normalizeQueryValue(value).toLowerCase()
  return normalized === "1" || normalized === "true"
}

function parsePageQuery(value: unknown): number {
  const normalized = normalizeQueryValue(value)
  const parsed = Number.parseInt(normalized, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
}

function applyQueryToFilters() {
  isSyncingFromRoute.value = true

  const roleCode = route.query?.role || "recipient"
  selectedRole.value = roleCode === "emitter" ? "emitter" : "recipient"

  const countryCodes = new Set(
    parseCsvQuery(route.query.countries).map((code) => code.toUpperCase()),
  )
  selectedCountries.value = countryOptions.value.filter((country) =>
    countryCodes.has(country.code.toUpperCase()),
  )

  isPartner.value = parseBooleanQuery(route.query.provider)
  isSCOSS.value = parseBooleanQuery(route.query.scoss)
  isPOSI.value = parseBooleanQuery(route.query.posi)
  isBarcelona.value = parseBooleanQuery(route.query.barcelona)
  currentPage.value = parsePageQuery(route.query.page)

  isSyncingFromRoute.value = false
}

function syncFiltersToQuery() {
  const roleCode = selectedRole.value
  const countryCodes = selectedCountries.value.map((country) =>
    country.code.toUpperCase(),
  )

  const nextQuery = {
    ...route.query,
    role: roleCode,
    provider: isPartner.value ? "true" : undefined,
    scoss: isSCOSS.value ? "true" : undefined,
    posi: isPOSI.value ? "true" : undefined,
    barcelona: isBarcelona.value ? "true" : undefined,
    page: currentPage.value > 1 ? String(currentPage.value) : undefined,
    countries: countryCodes.length > 0 ? countryCodes.join(",") : undefined,
  }

  void router.replace({ query: nextQuery, hash: route.hash })
}

function onPageChange(event: { page?: number }) {
  currentPage.value = (event.page ?? 0) + 1
}

const filteredEntities = computed(() => {
  const selectedCountryCodes = selectedCountries.value.map((country) =>
    country.code.toUpperCase(),
  )
  return allEntities.value
    .filter((entity) => {
      if (isPartner.value && !entity.is_partner) {
        return false
      }
      if (
        selectedRole.value == "recipient" &&
        isSCOSS.value &&
        !entity.is_scoss
      ) {
        return false
      }
      if (
        selectedRole.value == "recipient" &&
        isPOSI.value &&
        !entity.is_posi
      ) {
        return false
      }
      if (isBarcelona.value && !entity.is_barcelona) {
        return false
      }
      if (
        (selectedRole.value == "emitter" && entity.is_recipient) ||
        (selectedRole.value == "recipient" && !entity.is_recipient)
      ) {
        return false
      }
      if (
        selectedRole.value == "emitter" &&
        selectedCountries.value.length > 0
      ) {
        if (
          !entity.country ||
          !selectedCountryCodes.includes(entity.country.toUpperCase())
        ) {
          return false
        }
      }
      return true
    })
    .sort((a, b) => {
      // Sort by is_partner, has logo, and random
      const scoreA = (a.is_partner ? 3 : 0) + (a.logo ? 2 : 0)
      const scoreB = (b.is_partner ? 3 : 0) + (b.logo ? 2 : 0)
      return scoreB - scoreA + a.name.localeCompare(b.name)
    })
})
</script>

<template>
  <div class="container">
    <div class="container title-container">
      <h1 class="title">
        Explore the funding graph of<br />open science infrastructure
      </h1>
    </div>
    <div class="container select-container">
      <SelectButton
        v-model="selectedRole"
        :options="roleOptions"
        optionLabel="name"
        optionValue="code"
      />
    </div>
    <Divider class="divider" />
    <div class="container filter-container">
      <div class="filter-subcontainer">
        <p class="filter-title">Filter</p>
        <div class="filter-group">
          <div>
            <ToggleButton v-model="isPartner">
              <img src="/img/favicon-192x192.png" />
              <span class="p-togglebutton-label" data-pc-section="label"
                >TSOSI provider</span
              >
              <font-awesome-icon
                :icon="['fas', 'circle-question']"
                v-tooltip="{
                  value:
                    'Those who have shared data with TSOSI (see <a href=\'/pages/faq#data-provider\'>the FAQ</a>)',
                  escape: false,
                  autoHide: false,
                }"
              />
            </ToggleButton>
            <ToggleButton v-if="selectedRole == 'recipient'" v-model="isSCOSS">
              <img src="@/assets/img/scoss_icon.png" />
              <span class="p-togglebutton-label" data-pc-section="label"
                >SCOSS selected</span
              >
              <font-awesome-icon
                :icon="['fas', 'circle-question']"
                v-tooltip="{
                  value:
                    'infrastructures that have been selected by <a target=\'_blank\' href=\'https://scoss.org/\'>SCOSS</a>',
                  escape: false,
                  autoHide: false,
                }"
              />
            </ToggleButton>
            <ToggleButton v-if="selectedRole == 'recipient'" v-model="isPOSI">
              <img src="@/assets/img/posi_icon.ico" />
              <span class="p-togglebutton-label" data-pc-section="label"
                >POSI adopter</span
              >
              <font-awesome-icon
                :icon="['fas', 'circle-question']"
                v-tooltip="{
                  value:
                    'Infrastructures that have adopted the <a target=\'_blank\' href=\'https://openscholarlyinfrastructure.org/\'>POSI principles</a>',
                  escape: false,
                  autoHide: false,
                }"
              />
            </ToggleButton>
            <ToggleButton v-model="isBarcelona">
              <img src="@/assets/img/barcelona_icon.jpg" />
              <span class="p-togglebutton-label" data-pc-section="label"
                >Barcelona Declaration signatory</span
              >
              <font-awesome-icon
                :icon="['fas', 'circle-question']"
                v-tooltip="{
                  value:
                    'Signatories of the <a target=\'_blank\' href=\'https://barcelona-declaration.org/\'>Barcelona Declaration</a>',
                  escape: false,
                  autoHide: false,
                }"
              />
            </ToggleButton>
          </div>
          <div>
            <MultiSelect
              v-if="selectedRole == 'emitter'"
              v-model="selectedCountries"
              :options="countryOptions"
              optionLabel="name"
              placeholder="Select countries"
              display="chip"
              filter
              :showToggleAll="false"
            />
          </div>
        </div>
      </div>
      <!-- <div class="filter-subcontainer">
      <p class="filter-title">Sort</p>
      <Select
        v-model="selectedSort"
        :options="sortOptions"
        optionLabel="name"
        optionValue="code"
      />
    </div> -->
      <div class="counter-container">
        <p class="filter-title">
          Showing {{ filteredEntities.length }}
          {{ selectedRole == "emitter" ? "institutions" : "infrastructures" }}
        </p>
      </div>
    </div>
    <div class="container">
      <DataView
        :value="filteredEntities"
        layout="grid"
        dataKey="id"
        paginator
        :rows="rowsPerPage"
        :first="(currentPage - 1) * rowsPerPage"
        @page="onPageChange"
        class="entity-dataview"
      >
        <template #grid="slotProps">
          <div class="entities-grid">
            <EntityCard
              v-for="entity in slotProps.items"
              :key="entity.id"
              :entity="entity"
            />
          </div>
        </template>
      </DataView>
    </div>
  </div>
</template>

<style scoped>
.title-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 20px;
  margin-bottom: 20px;
}

.title {
  text-transform: none;
  font-size: 3em;
  text-align: center;
}

.select-container {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}
.select-container:deep(.p-togglebutton-label) {
  font-size: 1.5em;
  font-weight: bold;
}

.divider {
  margin: 15px;
  width: auto;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 15px;
  margin-bottom: 40px;
}

.filter-subcontainer {
  display: flex;
  flex-direction: row;
  justify-content: start;
  align-items: center;
}

.filter-group {
  display: flex;
  flex-direction: row;
  justify-content: start;
  align-items: center;
  flex-wrap: wrap;
}

.filter-title {
  display: inline;
  font-family: Mount;
  font-size: 1.15em;
  color: var(--p-primary-800);
  vertical-align: middle;
  font-weight: 700;
  margin: auto;
  margin-right: 20px;
}

.p-multiselect {
  width: 170px;
  margin: 0 5px;
}

.p-togglebutton {
  margin: 0 5px;
  height: 40px;
}

.p-togglebutton img {
  height: 1.2em;
  width: 1.2em;
}

.hidden {
  opacity: 0%;
}

.counter-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.entity-dataview {
  width: 100%;
}

.entities-grid {
  width: 100%;
  height: 100%;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 20px;
}

.icon-right:deep(.p-togglebutton-content) {
  flex-direction: row-reverse;
}
</style>
