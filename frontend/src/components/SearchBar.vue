<script setup lang="ts">
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import { computed, nextTick, ref, useTemplateRef, watch, type Ref } from "vue"

import EntityLinkDataAtom from "./atoms/EntityLinkDataAtom.vue"

import {
  entitySearch,
  queryPaginatedApiUrl,
  type ApiPaginatedData,
  type Entity,
} from "@/singletons/ref-data"
import debounce, { type DebounceStatus } from "@/utils/debounce"


interface SearchResult {
  id: string
  entity: Entity
  highlighted?: boolean
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
  fixed: boolean
  width?: string
  placeHolder?: string
  asGrowingButton?: boolean // Make the search bar smaller and growing on focus.
}

const props = defineProps<SearchBarProps>()

const op = useTemplateRef("op")
const component = useTemplateRef("search-bar")
const input = useTemplateRef("input")
const searchResultsEl = useTemplateRef("search-results")

// Search/query term
const searchTerm = ref("")
// The concatenated search results
const filteredResults: Ref<SearchResults> = ref(newEmptyResults())
// The currently selected item index
const highlightedIndex: Ref<number | undefined> = ref(undefined)
// The search status
const searchStatus: Ref<DebounceStatus> = ref("idle")

// Layout related refs
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
const pageSize = 20
const itemSize = 40

watch(highlightedIndex, updateHighlightedResult)

async function remoteOnSearch(event: Event) {
  const query = searchTerm.value.trim().toLowerCase()
  const results = await entitySearch(query)
  processResults(event, results, true)
}

const debouncedOnSearch = debounce(remoteOnSearch, 250, searchStatus)

/**
 * Query the next results page from the initial search query.
 * @param event
 */
async function queryNextResults(event: Event) {
  if (!filteredResults.value.next || searchStatus.value != "idle") {
    return
  }
  searchStatus.value = "running"
  const nextResults = (await queryPaginatedApiUrl(
    filteredResults.value.next,
  )) as ApiPaginatedData<Entity>
  processResults(event, nextResults, false)
  searchStatus.value = "idle"
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
    if (searchResultsEl.value) {
      searchResultsEl.value.scrollTo(0, 0)
    }
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
      id: e.id,
      entity: e,
    }
    categorizedResults.items[getItemCategory(e)].data.push(result)
  })
  filteredResults.value = categorizedResults
  showResults(event, newSearch)
}

/**
 * Show the popup containing the results.
 * The display is delayed if the search bar is styled as a growing button
 * to wait for the animation to end.
 *
 * @param event
 * @param reset
 */
function showResults(event: Event, reset = false) {
  if (props.asGrowingButton && !isFocused.value) {
    const wasOpen = isOpen.value
    isFocused.value = true
    if (!wasOpen) {
      // Trigger the results popup after the searchbar animation is finished
      setTimeout(() => showResults(event, reset), 800)
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

/**
 * Reset all refs and close the overlay.
 */
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
  // Whether the search bar need to fetch addidional data
  if (filteredResults.value.count >= filteredResults.value.total) {
    return
  }
  // When to query additional data
  const virtEl: HTMLElement = searchResultsEl.value!
  if (virtEl.scrollTop > virtEl.scrollHeight - (pageSize * itemSize) / 2) {
    queryNextResults(event)
  }
}

/**
 * Update the highlighted search result and scroll the results if required.
 */
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
  if (!searchResultsEl.value) {
    return
  }
  await nextTick()
  const highlighted = getHighlighted()
  if (!highlighted) {
    return
  }
  const rect = highlighted?.getBoundingClientRect()
  const virtEl: HTMLElement = searchResultsEl.value
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

/**
 * Unset top & bottom properties calculated by PrimeVue to make the popover
 * sticks to its parent.
 */
function onPopoverShow() {
  if (!props.fixed) {
    return
  }
  // @ts-expect-error Little hack to align the popover to the search bar.
  const popoverEl = op.value?.container || op.value?.$el.nextElementSibling
  if (!popoverEl) {
    return
  }
  popoverEl.style.top = "unset"
  popoverEl.style.bottom = "unset"
}
</script>

<template>
  <div class="search-bar" ref="search-bar">
    <IconField class="search-bar-input">
      <InputIcon class="search-bar-icon">
        <font-awesome-icon
          v-if="searchStatus == 'idle'"
          :icon="['fas', 'magnifying-glass']"
        />
        <font-awesome-icon
          v-else
          :icon="['fas', 'spinner']"
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
      :append-to="component || undefined"
      :baseZIndex="9999"
      :dt="{ gutter: 0 }"
      :style="`--width: ${elementWidth};`"
      @show="onPopoverShow()"
    >
      <div class="search-bar-overlay">
        <div v-if="filteredResults.count == 0" class="search-howto">
          <span v-if="searchStatus == 'idle' && searchTerm.trim().length > 0">
            No results for search "{{ searchTerm.trim() }}"<br />
          </span>
          <span>
            Search for supporters or infrastructures using their short name or
            full name (e.g., DOAJ, CNRS, Cornell, Couperin).
          </span>
        </div>

        <div
          v-else
          ref="search-results"
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
                <EntityLinkDataAtom
                  @click="resetSearchBar"
                  class="search-result"
                  :style="{ height: itemSize + 'px' }"
                  :class="{ highlighted: item.highlighted }"
                  :data="item"
                  :data-field="{
                    id: 'entity',
                    title: 'Entity',
                    field: 'entity',
                    type: 'entityLink',
                  }"
                />
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
      padding-inline-start: 2em;
    }

    .search-bar-icon {
      font-size: 1.8em;
      margin-top: -0.5em;
    }
  }
}
.search-bar:deep(.p-popover) {
  top: auto !important;
  left: auto !important;
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
  text-align: left;
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
  border-radius: 4x;
  text-decoration: none;

  &.highlighted,
  &:hover {
    cursor: pointer;
    background-color: var(--p-surface-200);
  }

  & :deep(.entity-label) {
    text-overflow: ellipsis;
    overflow: hidden;
  }
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

.entity-label {
  color: var(--color-text);
}
</style>
