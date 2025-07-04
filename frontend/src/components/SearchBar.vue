<script setup lang="ts">
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import { ref, type Ref, computed, watch, useTemplateRef, nextTick } from "vue"
import {
  entitySearch,
  type Entity,
  type ApiPaginatedData,
  queryPaginatedApiUrl,
} from "@/singletons/ref-data"
import { getEntityUrl } from "@/utils/url-utils"
import { RouterLink } from "vue-router"
import debounce, { type DebounceStatus } from "@/utils/debounce"

interface SearchResult {
  name: string
  url: string
  id: string
  highlighted?: boolean
  categoryId?: string
}
interface SearchResults {
  total: number
  count: number
  next: string | null
  items: {
    [categoryId: string]: {
      title: string
      data: SearchResult[]
    }
  }
  categoryOrder: string[]
}

export interface SearchBarProps {
  width?: string
  placeHolder?: string
  asGrowingButton?: boolean
}

const props = defineProps<SearchBarProps>()
const searchTerm = ref("")
const filteredResults: Ref<SearchResults> = ref(newEmptyResults())
const op = useTemplateRef("op")
const input = useTemplateRef("input")
const virtualScroll = useTemplateRef("virtual-scroll")
const highlightedIndex: Ref<number | undefined> = ref(undefined)
const isFocused = ref(false)
const isOpen = computed(() => {
  return (
    !props.asGrowingButton || searchTerm.value.length > 0 || isFocused.value
  )
})
const elementWidth = computed(() => `min(${props.width || "350px"}, 85vw)`)
const computedWidth = computed(() =>
  isOpen.value ? elementWidth.value : "100px",
)
const searchingStatus: Ref<DebounceStatus> = ref("idle")
const nextUrl: Ref<string | null> = ref(null)
const pageSize = 20

const itemSize = 40

watch(highlightedIndex, updateHighlightedResult)

async function remoteOnSearch(event: Event) {
  const query = searchTerm.value.trim().toLowerCase()
  const results = await entitySearch(query)
  processResults(event, results, true)
}

const debouncedOnSearch = debounce(remoteOnSearch, 250, searchingStatus)

/**
 * Query the next results page from the initial search query.
 * @param event
 */
async function queryNextResults(event: Event) {
  if (!filteredResults.value.next || searchingStatus.value != "idle") {
    return
  }
  searchingStatus.value = "running"
  const nextResults = (await queryPaginatedApiUrl(
    filteredResults.value.next,
  )) as ApiPaginatedData<Entity>
  processResults(event, nextResults, false)
  searchingStatus.value = "idle"
}

function getItemCategory(e: Entity): string {
  return e.is_recipient ? "infra" : "supporter"
}
/**
 * Process the API results
 * @param event The event that triggered the search
 * @param results The API results
 * @param newSearch Whether it's a search with a new query or the fetching
 *                  of the next results page.
 */
function processResults(
  event: Event,
  results: ApiPaginatedData<Entity> | null,
  newSearch = false,
) {
  if (newSearch) {
    filteredResults.value = newEmptyResults()
  }
  if (!results) {
    return
  }
  const categorizedResults: SearchResults = {
    ...filteredResults.value,
  }
  categorizedResults.total = results.count
  categorizedResults.count += results.results.length
  categorizedResults.next = results.next

  results.results.forEach((e) => {
    const result = {
      name: e.name,
      url: getEntityUrl(e),
      id: e.id,
    }
    categorizedResults.items[getItemCategory(e)].data.push(result)
  })
  nextUrl.value = results.next
  filteredResults.value = categorizedResults
  showResults(event, newSearch)
}

function showResults(event: Event, reset = false) {
  if (props.asGrowingButton && !isFocused.value) {
    const wasOpen = isOpen.value
    isFocused.value = true
    if (!wasOpen) {
      // Trigger the results popup after the searchbar animation is finished
      setTimeout(() => showResults(event), 800)
      return
    }
  }
  if (reset) {
    highlightedIndex.value = undefined
  }
  // @ts-expect-error PrimeVue component declaration omits basic
  // VueJS attributes..
  op.value!.show(event, input.value!.$el)
}

function newEmptyResults(): SearchResults {
  return {
    total: 0,
    count: 0,
    next: null,
    items: {
      infra: {
        title: "Infrastructures",
        data: [],
      },
      supporter: {
        title: "Supporters",
        data: [],
      },
    },
    categoryOrder: ["infra", "supporter"],
  }
}

function resetSearchBar() {
  op.value!.hide()
  searchTerm.value = ""
  filteredResults.value = newEmptyResults()
  highlightedIndex.value = undefined
}

function getHighlighted(): HTMLElement | null {
  return document.querySelector(".search-result.highlighted")
}

function onKeyDown(event: KeyboardEvent) {
  if (!["ArrowDown", "ArrowUp", "Enter"].includes(event.key)) {
    return
  }
  if (event.key == "Enter") {
    getHighlighted()?.click()
    return
  }
  const resultsLength = filteredResults.value.count
  if (resultsLength == 0) {
    return
  }

  event.stopImmediatePropagation()

  if (event.key === "ArrowDown") {
    if (highlightedIndex.value === undefined) {
      highlightedIndex.value = 0
    } else if (highlightedIndex.value < resultsLength - 1) {
      highlightedIndex.value += 1
    }
  } else if (event.key === "ArrowUp") {
    if (highlightedIndex.value && highlightedIndex.value > 0) {
      highlightedIndex.value -= 1
      // @ts-expect-error PrimeVue component declaration omits basic
      // VueJS attributes..
      const inputEl: HTMLInputElement = input.value.$el
      inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length)
      setTimeout(
        () =>
          inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length),
        50,
      )
    }
  }
}

/**
 * When the virtual scroller is scrolled, we query additional data if required.
 * @param event
 */
function onVirtualScroll(event: Event) {
  // @ts-expect-error PrimeVue component declaration omits basic
  // VueJS attributes..
  // const virtEl: HTMLElement = virtualScroll.value.$el
  const virtEl: HTMLElement = virtualScroll.value
  if (
    virtEl.scrollHeight >= pageSize * itemSize &&
    virtEl.scrollTop > virtEl.scrollHeight - (pageSize * itemSize) / 2
  ) {
    queryNextResults(event)
  }
}

async function updateHighlightedResult() {
  for (const category in filteredResults.value.items) {
    filteredResults.value.items[category].data.forEach(
      (r) => (r.highlighted = false),
    )
  }
  if (highlightedIndex.value === undefined) {
    return
  }
  let index = 0
  for (const cId of filteredResults.value.categoryOrder) {
    const category = filteredResults.value.items[cId]
    const catCount = category.data.length
    if (highlightedIndex.value < index + catCount) {
      category.data[highlightedIndex.value - index].highlighted = true
      break
    }
    index += catCount
  }
  // Might be needed to trigger ref update??
  const data = filteredResults.value
  filteredResults.value = data
  if (!virtualScroll.value) {
    return
  }
  await nextTick()
  const highlighted = getHighlighted()
  if (!highlighted) {
    return
  }
  const rect = highlighted?.getBoundingClientRect()
  const virtEl: HTMLElement = virtualScroll.value
  const virtRect = virtEl.getBoundingClientRect()
  // We add some margin for the up scrolling because of the sticky
  // category titles
  const virtTop = virtRect.top + 40
  if (rect.top < virtTop) {
    virtEl.scrollBy(0, rect.top - virtTop)
  } else if (rect.bottom > virtRect.bottom) {
    virtEl.scrollBy(0, rect.bottom - virtRect.bottom)
  }
}

function focusOut() {
  isFocused.value = false
  highlightedIndex.value = undefined
  if (!searchTerm.value) {
    op.value!.hide()
  }
}
</script>

<template>
  <div class="search-bar">
    <IconField class="search-bar-input">
      <InputIcon class="search-bar-icon">
        <font-awesome-icon
          v-if="searchingStatus == 'idle'"
          icon="fa-solid fa-magnifying-glass"
        />
        <font-awesome-icon
          v-else
          icon="fa-solid fa-spinner"
          class="loader-icon-animate"
        />
      </InputIcon>
      <InputText
        ref="input"
        v-model="searchTerm"
        :placeholder="props.placeHolder ?? 'Search'"
        @input="debouncedOnSearch"
        @focus="showResults"
        @focusout="focusOut"
        :onKeydown="onKeyDown"
        style="width: 100%"
        :dt="{ paddingX: '0' }"
      />
    </IconField>
    <Popover
      ref="op"
      class="popover-no-arrow"
      :baseZIndex="9999"
      :dt="{ gutter: 0 }"
      :style="`--width: ${elementWidth};`"
    >
      <div class="search-bar-overlay">
        <div v-if="filteredResults.count == 0" class="search-howto">
          <span
            v-if="searchingStatus == 'idle' && searchTerm.trim().length > 0"
          >
            No results for search "{{ searchTerm.trim() }}"<br />
          </span>
          You can search for infrastructures or supporters:
          <ul>
            <li>
              Search by name: e.g. "Peer Community In" or "Université Grenoble
              Alpes"
            </li>
            <li>Search by ROR ID: e.g. "0315saa81" or "02rx3b187"</li>
            <li>Search by Wikidata ID: e.g. "Q97368331" or "Q945876"</li>
          </ul>
        </div>
        <div
          v-else
          ref="virtual-scroll"
          class="search-results"
          @scroll="onVirtualScroll"
          style="max-height: 300px"
        >
          <div
            v-for="categoryId of filteredResults.categoryOrder"
            :key="categoryId"
          >
            <div
              v-if="filteredResults.items[categoryId]?.data.length"
              class="search-category"
            >
              <h3 class="search-category-title">
                {{ filteredResults.items[categoryId].title }}
              </h3>
              <div
                v-for="item of filteredResults.items[categoryId].data"
                :key="item.id"
              >
                <RouterLink
                  :to="item.url"
                  @click="resetSearchBar"
                  class="search-result"
                  :style="{ height: itemSize + 'px' }"
                  :class="{ highlighted: item.highlighted }"
                  :title="item.name"
                >
                  <span class="search-result-text">
                    {{ item.name }}
                  </span>
                </RouterLink>
              </div>
            </div>
          </div>
        </div>
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
  width: v-bind(computedWidth);
  transition: width 0.1s ease-in;
}
.search-bar-overlay {
  --content-width: calc(var(--width) - 20px);
  position: relative;
  max-width: var(--content-width);
  width: var(--content-width);
  overflow: hidden;
}

.search-results {
  overflow-x: hidden;
  position: relative;
}

.search-howto {
  width: 100%;
}

.search-result {
  display: flex;
  align-items: center;
  text-wrap: nowrap;
  max-width: var(--content-width);
  padding: 2px 4px;
  border-radius: 4x;
  text-decoration: unset;

  &.highlighted,
  &:hover {
    cursor: pointer;
    background-color: var(--p-surface-200);
    text-decoration: underline;
  }
}

.search-result-text {
  text-overflow: ellipsis;
  overflow: hidden;
}

.loader-icon-animate {
  animation: uniform-spinning 1s linear infinite;
}

.search-category {
  position: relative;
}

.search-category-title {
  position: sticky;
  top: 0;
  background-color: var(--color-background);
  padding: 0.35em 0;
}

@keyframes uniform-spinning {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
