<script setup lang="ts">
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import VirtualScroller from "primevue/virtualscroller"
import {
  onMounted,
  ref,
  type Ref,
  computed,
  watch,
  useTemplateRef,
  nextTick,
} from "vue"
import { getEntities } from "@/singletons/ref-data"
import { getEntityUrl } from "@/utils/url-utils"
import { RouterLink } from "vue-router"

interface searchResult {
  name: string
  url: string
  matchable: string[]
  highlighted?: boolean
}
export interface SearchBarProps {
  width?: string
  placeHolder?: string
  asGrowingButton?: boolean
}

const props = defineProps<SearchBarProps>()
const searchTerm = ref("")
const searchResults: Ref<Array<searchResult>> = ref([])
const filteredResults: Ref<Array<searchResult>> = ref([])
const loading = ref(true)
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

const itemSize = 40

onMounted(async () => getEntitiesForSearch())
watch(highlightedIndex, updateHighlightedResult)

function onSearch(event: Event) {
  const query = searchTerm.value.trim().toLowerCase()
  highlightedIndex.value = undefined
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

function showResults(event: Event) {
  if (props.asGrowingButton && !isFocused.value) {
    const wasOpen = isOpen.value
    isFocused.value = true
    if (!wasOpen) {
      // Trigger the results popup after the searchbar animation is finished
      setTimeout(() => showResults(event), 800)
      return
    }
  }
  highlightedIndex.value = undefined
  // @ts-expect-error PrimeVue component declaration omits basic
  // VueJS attributes..
  op.value!.show(event, input.value!.$el)
}

function resetSearchBar() {
  op.value!.hide()
  searchTerm.value = ""
  filteredResults.value = []
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
  const resultsLength = filteredResults.value.length
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

async function updateHighlightedResult() {
  filteredResults.value.forEach((res) => (res.highlighted = false))
  if (highlightedIndex.value === undefined) {
    return
  }
  const data = filteredResults.value
  data[highlightedIndex.value].highlighted = true
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
  // @ts-expect-error PrimeVue component declaration omits basic
  // VueJS attributes..
  const virtEl: HTMLElement = virtualScroll.value.$el
  const virtRect = virtEl.getBoundingClientRect()

  if (rect.top < virtRect.top) {
    virtEl.scrollBy(0, rect.top - virtRect.top)
  } else if (rect.bottom > virtRect.bottom) {
    virtEl.scrollBy(0, rect.bottom - virtRect.bottom)
  }
}

function focusOut() {
  isFocused.value = false
  highlightedIndex.value = undefined
  // op.value!.hide()
}
</script>

<template>
  <div class="search-bar">
    <IconField class="search-bar-input">
      <InputIcon class="search-bar-icon">
        <font-awesome-icon icon="magnifying-glass" />
      </InputIcon>
      <InputText
        ref="input"
        v-model="searchTerm"
        :placeholder="props.placeHolder ?? 'Search'"
        @input="onSearch"
        @focus="showResults"
        @focusout="focusOut"
        :onKeydown="onKeyDown"
        style="width: 100%"
      />
    </IconField>
    <Popover
      ref="op"
      :baseZIndex="9999"
      :dt="{ gutter: 0 }"
      :style="`--width: ${elementWidth};`"
    >
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
          ref="virtual-scroll"
          :items="filteredResults"
          :itemSize="itemSize"
          class="search-results"
          orientation="vertical"
          :scroll-height="virtualScrollerHeight"
        >
          <template #item="{ item }">
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
</style>
