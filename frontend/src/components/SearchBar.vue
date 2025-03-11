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

export interface SearchBarProps {
  width?: string
  placeHolder?: string
}

const props = defineProps<SearchBarProps>()
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

const elementWidth = computed(() => `min(${props.width || "350px"}, 85vw)`)
</script>

<template>
  <div class="search-bar">
    <IconField class="search-bar-input">
      <InputIcon class="search-bar-icon">
        <font-awesome-icon icon="magnifying-glass" />
      </InputIcon>
      <InputText
        v-model="searchTerm"
        :placeholder="props.placeHolder ?? 'Search'"
        @input="onSearch"
        @focus="showResults"
        style="width: 100%"
      />
    </IconField>
    <Popover ref="op" :baseZIndex="9999" :style="`--width: ${elementWidth}`">
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
          orientation="vertical"
          :scroll-height="virtualScrollerHeight"
        >
          <template #item="{ item }">
            <div class="search-result" :style="{ height: itemSize + 'px' }">
              <RouterLink
                :to="item.url"
                @click="resetSearchBar"
                class="search-result-text"
              >
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
.search-bar {
  text-align: center;

  &.large {
    .search-bar-input :deep(input) {
      font-size: 1.8rem;
      /* padding-inline: 0.75em;
      padding-block: 0.5em; */
      padding-inline-start: 2em;
    }

    .search-bar-icon {
      font-size: 1.8em;
      margin-top: -0.5em;
    }
  }
}

.search-bar-input {
  display: inline-block;
  width: v-bind(elementWidth);
}
.search-bar-overlay {
  --content-width: calc(var(--width) - 20px);
  position: relative;
  max-width: var(--content-width);
  width: var(--content-width);
  overflow: scroll;
}

.search-howto {
  width: 100%;
}

.search-result {
  display: flex;
  align-items: center;
  text-wrap: nowrap;
  max-width: var(--content-width);
}

.search-result-text {
  text-overflow: ellipsis;
  overflow: hidden;
}
</style>
