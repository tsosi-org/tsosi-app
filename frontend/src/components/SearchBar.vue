<script setup lang="ts">
import IconField from "primevue/iconfield"
import InputIcon from "primevue/inputicon"
import InputText from "primevue/inputtext"
import Popover from "primevue/popover"
import {
  computed,
  nextTick,
  onBeforeMount,
  onMounted,
  ref,
  useTemplateRef,
} from "vue"
import { RouterLink, useRouter } from "vue-router"

import EntityLinkDataAtom from "@/components/atoms/EntityLinkDataAtom.vue"
import {
  searchOrganizations,
  type RegistryRecord,
} from "@/singletons/hub-organizations"
import {
  entitySearch,
  getEntities,
  queryPaginatedApiUrl,
  type ApiPaginatedData,
  type DeepReadonly,
  type Entity,
} from "@/singletons/ref-data"
import { shuffleArray } from "@/utils/data-utils"
import debounce, { type DebounceStatus } from "@/utils/debounce"
import { getEntityUrl } from "@/utils/url-utils"

/**
 * The search over the organizations, their results shown with their name
 * and icon, by role. On the site (header), it searches the public ones, its
 * results opening their page. In the Hub (`hub`), it picks an organization,
 * public or not; a ROR or Wikidata ID missing from TSOSI gives its record,
 * to add the organization, and the last option adds one from its name.
 */
export interface SearchBarProps {
  fixed?: boolean
  width?: string
  placeHolder?: string
  // Make the search bar smaller and growing on focus
  asGrowingButton?: boolean
  // Pick an organization of the Hub instead of opening its page
  hub?: boolean
  invalid?: boolean
  autofocus?: boolean
}

const props = defineProps<SearchBarProps>()
const emit = defineEmits<{
  select: [entity: DeepReadonly<Entity>]
  // Add the organization of a ROR or Wikidata record
  addRecord: [record: RegistryRecord]
  // Add an organization from its name, the one searched
  add: [name: string]
}>()

const router = useRouter()
const popover = useTemplateRef("popover")
const component = useTemplateRef("search-bar")
const input = useTemplateRef("input")
const resultsElement = useTemplateRef("results")

// A result: an organization, the record of an ID, adding an organization
// from the name searched, or an error
interface Option {
  id: string
  category: string
  entity?: DeepReadonly<Entity>
  record?: RegistryRecord
  action?: "add" | "error"
  text?: string
}

// The results are grouped by role, then the Hub's other options
const categories: { id: string; title?: string }[] = [
  { id: "infra", title: "Infrastructures" },
  { id: "supporter", title: "Supporters" },
  { id: "actions" },
]

function roleCategory(entity: DeepReadonly<Entity>): string {
  return entity.is_recipient ? "infra" : "supporter"
}

const searchTerm = ref("")
const options = ref<Option[]>([])
// The site's results are paginated
const total = ref(0)
const next = ref<string | null>(null)
const highlightedIndex = ref<number | null>(null)
const searchStatus = ref<DebounceStatus>("idle")
// Only the last search's results are shown
let searchCount = 0

const isFocused = ref(false)
const isOpen = computed(
  () =>
    !props.asGrowingButton || searchTerm.value.length > 0 || isFocused.value,
)
const elementWidth = computed(() =>
  props.hub ? "100%" : `min(${props.width || "350px"}, 85vw)`,
)
const inputWidth = computed(() => (isOpen.value ? elementWidth.value : "100px"))
// The Hub's search is in a table cell: its results can be wider
const overlayWidth = ref(elementWidth.value)
const minimumQueryLength = props.hub ? 2 : 1

const groups = computed(() =>
  categories
    .map((category) => ({
      ...category,
      options: options.value.filter((o) => o.category == category.id),
    }))
    .filter((group) => group.options.length),
)

const exampleEntities = ref<string[]>([])

onBeforeMount(async () => {
  if (props.hub) {
    return
  }
  const loadedEntities = Object.values((await getEntities()) || {}) as Entity[]
  shuffleArray(loadedEntities)
  exampleEntities.value = loadedEntities
    .filter((e) => !e.is_recipient && e.is_partner)
    .slice(0, 3)
    .concat(
      loadedEntities.filter((e) => e.is_recipient && e.is_partner).slice(0, 3),
    )
    .map((e) => e?.short_name || e.name)
    .filter((e) => !!e)
})

onMounted(async () => {
  if (props.autofocus) {
    // Once the popover's portal is rendered: shown before, its transition
    // starts visible, without positioning it (the results end up at the
    // bottom of the page)
    await nextTick()
    inputElement()?.focus()
  }
})

function inputElement(): HTMLInputElement | undefined {
  // @ts-expect-error PrimeVue's component type omits `$el`
  return input.value?.$el
}

// The options in their groups' order, which is the display's
function sortOptions(list: Option[]): Option[] {
  const order = categories.map((c) => c.id)
  return [...list].sort(
    (a, b) => order.indexOf(a.category) - order.indexOf(b.category),
  )
}

function siteOptions(results: ApiPaginatedData<Entity>): Option[] {
  return results.results.map((entity) => ({
    id: entity.id,
    category: roleCategory(entity),
    entity,
  }))
}

async function hubOptions(query: string): Promise<Option[]> {
  const result = await searchOrganizations(query)
  const list: Option[] = []
  if (!result) {
    list.push({
      id: "__error",
      category: "actions",
      action: "error",
      text: "The search failed. Please try again.",
    })
  } else {
    list.push(
      ...result.results.map((entity) => ({
        id: entity.id,
        category: roleCategory(entity),
        entity,
      })),
    )
    if (result.lookup?.record) {
      list.push({
        id: "__record",
        category: "actions",
        record: result.lookup.record,
      })
    } else if (result.lookup?.error) {
      list.push({
        id: "__error",
        category: "actions",
        action: "error",
        text: result.lookup.error,
      })
    }
  }
  list.push({ id: "__add", category: "actions", action: "add", text: query })
  return list
}

async function search() {
  const query = searchTerm.value.trim()
  const current = ++searchCount
  if (query.length < minimumQueryLength) {
    options.value = []
    next.value = null
    return
  }
  let list: Option[]
  if (props.hub) {
    list = await hubOptions(query)
  } else {
    const results = await entitySearch(query.toLowerCase())
    if (current != searchCount) {
      return
    }
    list = results ? siteOptions(results) : []
    total.value = results?.count ?? 0
    next.value = results?.next ?? null
  }
  if (current != searchCount) {
    return
  }
  options.value = sortOptions(list)
  highlightedIndex.value = null
  resultsElement.value?.scrollTo(0, 0)
  show()
}

const debouncedSearch = debounce(search, 250, searchStatus)

// The site's next results, once its results are scrolled to their end
async function onScroll() {
  const element = resultsElement.value
  if (
    !next.value ||
    searchStatus.value != "idle" ||
    !element ||
    element.scrollTop + element.clientHeight < element.scrollHeight - 200
  ) {
    return
  }
  searchStatus.value = "running"
  const current = searchCount
  const results = await queryPaginatedApiUrl<Entity>(next.value)
  searchStatus.value = "idle"
  if (!results || current != searchCount) {
    return
  }
  next.value = results.next
  options.value = sortOptions([...options.value, ...siteOptions(results)])
}

/**
 * Show the results. The growing search bar shows them once its animation
 * ends.
 */
function show() {
  if (props.asGrowingButton && !isFocused.value) {
    const wasOpen = isOpen.value
    isFocused.value = true
    if (!wasOpen) {
      setTimeout(show, 800)
      return
    }
  }
  const element = inputElement()
  if (!element) {
    return
  }
  if (props.hub) {
    overlayWidth.value = `${Math.max(element.offsetWidth, 352)}px`
  }
  popover.value?.show({ currentTarget: element } as unknown as Event, element)
}

function reset() {
  popover.value?.hide()
  searchTerm.value = ""
  options.value = []
  next.value = null
  highlightedIndex.value = null
  searchCount++
}

function choose(option: Option) {
  if (option.action == "error") {
    return
  }
  if (!props.hub) {
    router.push(getEntityUrl(option.entity as Entity))
  } else if (option.entity) {
    emit("select", option.entity)
  } else if (option.record) {
    emit("addRecord", option.record)
  } else {
    emit("add", option.text!)
  }
  reset()
}

async function highlight(index: number) {
  highlightedIndex.value = index
  await nextTick()
  resultsElement.value
    ?.querySelector(".search-result.highlighted")
    ?.scrollIntoView({ block: "nearest" })
}

function onKeyDown(event: KeyboardEvent) {
  const count = options.value.length
  if (event.key == "Escape") {
    popover.value?.hide()
  } else if (event.key == "Enter" && highlightedIndex.value != null) {
    event.preventDefault()
    choose(options.value[highlightedIndex.value])
  } else if (event.key == "ArrowDown" && count) {
    event.preventDefault()
    const index = highlightedIndex.value
    highlight(index == null ? 0 : Math.min(index + 1, count - 1))
  } else if (event.key == "ArrowUp" && count) {
    event.preventDefault()
    highlight(Math.max((highlightedIndex.value ?? 0) - 1, 0))
  }
}

// Leaving the search closes its results: clicking them keeps the focus in
// the search (see the overlay's mousedown)
function onFocusOut() {
  isFocused.value = false
  highlightedIndex.value = null
  popover.value?.hide()
}

/**
 * Unset the top and bottom positions computed by PrimeVue, so that the
 * results stick to the fixed header's search bar.
 */
function onPopoverShow() {
  if (!props.fixed) {
    return
  }
  // Little hack to align the popover to the search bar: PrimeVue's type
  // omits these attributes
  const component = popover.value as any
  const element: HTMLElement | undefined =
    component?.container || component?.$el.nextElementSibling
  if (!element) {
    return
  }
  element.style.top = "unset"
  element.style.bottom = "unset"
}

const registryLabels: Record<string, string> = {
  ror: "ROR",
  wikidata: "Wikidata",
}

const entityField = {
  id: "entity",
  title: "Entity",
  field: "entity",
  type: "entityLink" as const,
}
</script>

<template>
  <div class="search-bar" :class="{ hub: props.hub }" ref="search-bar">
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
        :invalid="props.invalid"
        role="combobox"
        aria-autocomplete="list"
        @input="debouncedSearch"
        @focus="show"
        @focusout="onFocusOut"
        @keydown="onKeyDown"
        style="width: 100%"
        :dt="{ paddingX: '0' }"
      />
    </IconField>

    <!-- In the Hub, the results float over the table, out of its cell -->
    <Popover
      ref="popover"
      class="popover-no-arrow"
      :append-to="props.hub ? 'body' : component || undefined"
      :baseZIndex="9999"
      :dt="{ gutter: 0 }"
      :style="`--width: ${props.hub ? overlayWidth : elementWidth};`"
      @show="onPopoverShow()"
    >
      <div class="search-bar-overlay" @mousedown.prevent>
        <div v-if="!options.length" class="search-howto">
          <template v-if="props.hub">
            Type a name, or a ROR or Wikidata ID.
          </template>
          <template v-else>
            <span v-if="searchStatus == 'idle' && searchTerm.trim().length > 0">
              No results for search "{{ searchTerm.trim() }}"<br />
            </span>
            <span>
              {{
                `Search for supporters or infrastructures such as ${exampleEntities.slice(0, -1).join(", ")} or ${exampleEntities.at(-1)}`
              }}
            </span>
          </template>
        </div>

        <div
          v-else
          ref="results"
          class="search-results"
          role="listbox"
          @scroll="onScroll"
        >
          <div v-for="group of groups" :key="group.id" class="search-category">
            <h3 v-if="group.title" class="search-category-title">
              {{ group.title }}
            </h3>
            <!-- The site's results are links to their page, whole -->
            <component
              :is="props.hub || !option.entity ? 'div' : RouterLink"
              v-for="option of group.options"
              :key="option.id"
              :to="
                props.hub || !option.entity
                  ? undefined
                  : getEntityUrl(option.entity as Entity)
              "
              class="search-result"
              :class="{
                highlighted: options.indexOf(option) == highlightedIndex,
                action: !option.entity,
                error: option.action == 'error',
              }"
              role="option"
              :aria-selected="options.indexOf(option) == highlightedIndex"
              @click="props.hub ? choose(option) : reset()"
            >
              <EntityLinkDataAtom
                v-if="option.entity"
                :data="option"
                :dataField="entityField"
                noLink
              />
              <span v-else-if="option.record" class="add-option">
                <font-awesome-icon :icon="['fas', 'plus']" />
                Add from {{ registryLabels[option.record.registry] }}:
                {{ option.record.name ?? option.record.identifier }}
              </span>
              <span v-else-if="option.action == 'add'" class="add-option">
                <font-awesome-icon :icon="['fas', 'plus']" />
                Not found? Add a new organization
              </span>
              <span v-else>{{ option.text }}</span>
            </component>
          </div>
        </div>
      </div>
    </Popover>
  </div>
</template>

<style scoped>
.search-bar {
  text-align: center;

  &.hub {
    text-align: left;
  }
}

.search-bar:not(.hub):deep(.p-popover) {
  top: auto !important;
  left: auto !important;
}

.search-bar-input {
  display: inline-block;
  width: v-bind(inputWidth);
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
  position: relative;
  max-height: 300px;
  overflow-x: hidden;
  overflow-y: auto;
}

.search-results a {
  color: inherit;
  text-decoration: none;
}

.search-howto {
  width: 100%;
}

.search-result {
  display: flex;
  align-items: center;
  min-height: 40px;
  max-width: var(--content-width);
  border-radius: 4px;
  text-wrap: nowrap;
  cursor: pointer;

  &.highlighted,
  &:hover {
    background-color: var(--p-surface-200);
  }

  &.error {
    color: var(--p-red-600);
    text-wrap: wrap;
    cursor: default;

    &:hover {
      background: none;
    }
  }

  & :deep(.entity-label) {
    text-overflow: ellipsis;
    overflow: hidden;
  }
}

.add-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.3rem;
  color: var(--p-primary-color);
  font-weight: 600;
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
</style>
