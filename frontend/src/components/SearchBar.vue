<script setup lang="ts">
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import VirtualScroller from "primevue/virtualscroller"
import { onMounted, ref, type Ref, computed } from "vue"
import { getEntities } from "@/singletons/ref-data"
import { getEntityUrl } from "@/utils/url-utils"
import { RouterLink } from "vue-router"

const searchTerm = ref("")
interface searchResult {
  name: string
  url: string
  matchable: string[]
}
const searchResults: Ref<Array<searchResult>> = ref([])
const filteredResults: Ref<Array<searchResult>> = ref([])
const loading = ref(true)
const op = ref()

const itemSize = 35

onMounted(async () => getEntitiesForSearch())

function onSearch(event: Event) {
  const query = searchTerm.value.trim().toLowerCase()
  if (searchResults.value.length == 0 || !query.length) {
    filteredResults.value = []
    return
  }
  filteredResults.value = searchResults.value.filter((result) =>
    result.matchable.some((val) => val.includes(query)),
  )
  showResults(event)
}

async function getEntitiesForSearch() {
  const entities = await getEntities()
  if (entities == null) {
    return
  }
  const baseData: Array<searchResult> = []

  for (const id in entities) {
    const entity = entities[id]
    const matchable = [
      entity.name.toLowerCase(),
      ...entity.identifiers.map((i) => i.value.toLowerCase()),
    ]
    const entityResult = {
      name: entity.name,
      url: getEntityUrl(id),
      matchable: matchable,
    }
    baseData.push(entityResult)
    searchResults.value = baseData
  }
  loading.value = false
}

const virtualScrollerHeight = computed(() => {
  const size = filteredResults.value.length * itemSize
  return `${size > 300 ? 300 : size}px`
})

const showResults = (event: Event) => {
  op.value.show(event)
}

function resetSearchBar(event: Event) {
  op.value.hide(event)
  searchTerm.value = ""
  filteredResults.value = []
}
</script>

<template>
  <div class="search-bar">
    <IconField>
      <InputIcon>
        <font-awesome-icon icon="magnifying-glass" />
      </InputIcon>
      <InputText
        v-model="searchTerm"
        placeholder="Search"
        @input="onSearch"
        @focus="showResults"
      />
    </IconField>
    <Popover ref="op">
      <div class="search-bar-overlay">
        <div v-if="filteredResults.length == 0" class="search-howto">
          <span v-if="searchTerm.trim().length > 0">
            No results for search "{{ searchTerm.trim() }}"<br />
          </span>
          You can search for infrastructures or supporters:
          <ul>
            <li>
              Search by name: e.g. "Peer Community In" or "University Grenoble
              Alpes"
            </li>
            <li>Search by ROR ID: e.g. "0315saa81" or "02rx3b187"</li>
            <li>Search by Wikidata ID: e.g. "Q97368331" or "Q945876"</li>
          </ul>
        </div>
        <VirtualScroller
          v-else
          :items="filteredResults"
          :itemSize="itemSize"
          class="search-results"
          :scroll-height="virtualScrollerHeight"
        >
          <template #item="{ item }">
            <div class="search-result" :style="{ height: itemSize + 'px' }">
              <RouterLink :to="item.url" @click="resetSearchBar">
                {{ item.name }}
              </RouterLink>
            </div>
          </template>
        </VirtualScroller>
      </div>
    </Popover>
  </div>
</template>

<style scoped>
.search-bar-overlay {
  width: 350px;
  overflow: scroll;
  /* max-height: 300px; */
}

.search-howto {
  width: 100%;
}

.search-results {
  max-width: 350px;
}

.search-result {
  display: flex;
  align-items: center;
  text-wrap: nowrap;
  text-overflow: ellipsis;
  max-width: 350px;
}
</style>
