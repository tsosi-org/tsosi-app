<script setup lang="ts">
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import { computed, onMounted, ref, useId } from "vue"

import Message from "@/components/atoms/MessageAtom.vue"
import {
  addOrganization,
  parseOrganizationId,
  searchOrganizations,
  type RegistryRecord,
} from "@/singletons/hub-organizations"
import type { DeepReadonly, Entity } from "@/singletons/ref-data"
import debounce, { type DebounceStatus } from "@/utils/debounce"

/**
 * Add an organization missing from TSOSI, the beneficiary or an
 * intermediary: from its ROR or Wikidata ID, whose record is looked up as
 * it's typed (TSOSI then gets its details from there), or else from its
 * name. An ID already in TSOSI gives its organization, to pick instead.
 */
const props = defineProps<{
  // The organization whose Hub it is
  organizationId: string
  // The cell it's added for
  field: "agents" | "recipient"
  // The text searched
  initialName: string
}>()
const emit = defineEmits<{
  added: [entity: Entity]
  cancel: []
}>()

const REGISTRY_LABELS: Record<string, string> = {
  ror: "ROR",
  wikidata: "Wikidata",
}

const idPrefix = useId()
const text = ref(props.initialName)
const errors = ref<Record<string, string>>({})
const busy = ref(false)

const title = computed(() =>
  props.field == "recipient" ? "Add an infrastructure" : "Add an intermediary",
)

// The ID typed, if it's one
const typedId = computed(() => parseOrganizationId(text.value))

// The lookup of the ID typed: its record, the organization already in TSOSI
// with it, or the error
interface Lookup {
  id: string
  record: RegistryRecord | null
  entity: DeepReadonly<Entity> | null
  error: string | null
}
const lookup = ref<Lookup | null>(null)
const lookupStatus = ref<DebounceStatus>("idle")
// Only the last lookup's result is shown
let lookupCount = 0

async function runLookup() {
  const id = typedId.value
  const current = ++lookupCount
  if (!id) {
    lookup.value = null
    return
  }
  const result = await searchOrganizations(id.value)
  if (current != lookupCount) {
    return
  }
  if (!result) {
    lookup.value = {
      id: id.value,
      record: null,
      entity: null,
      error: "The lookup failed. Please try again.",
    }
    return
  }
  // Already in TSOSI: the organization with this ID, first
  const entity = result.lookup
    ? null
    : (result.results.find((e) =>
        e.identifiers.some(
          (i) => i.value.toLowerCase() == id.value.toLowerCase(),
        ),
      ) ??
      result.results[0] ??
      null)
  lookup.value = {
    id: id.value,
    record: result.lookup?.record ?? null,
    entity,
    error: result.lookup?.error ?? null,
  }
}

const debouncedLookup = debounce(runLookup, 400, lookupStatus)

function onInput() {
  errors.value = {}
  lookup.value = null
  if (typedId.value) {
    debouncedLookup()
  } else {
    lookupCount++
  }
}

onMounted(() => {
  if (typedId.value) {
    runLookup()
  }
})

// The current lookup, once done for the ID typed
const currentLookup = computed(() =>
  lookup.value && lookup.value.id == typedId.value?.value ? lookup.value : null,
)

const submitLabel = computed(() => {
  if (currentLookup.value?.entity) {
    return "Pick this organization"
  }
  if (typedId.value) {
    return `Add from ${REGISTRY_LABELS[typedId.value.registry]}`
  }
  return "Add from its name"
})

async function add() {
  if (busy.value) {
    return
  }
  const value = text.value.trim()
  if (!value) {
    errors.value = {
      text: "Enter the organization's ROR or Wikidata ID, or its name.",
    }
    return
  }
  if (currentLookup.value?.entity) {
    emit("added", currentLookup.value.entity as Entity)
    return
  }
  if (currentLookup.value?.error) {
    errors.value = { text: currentLookup.value.error }
    return
  }
  busy.value = true
  errors.value = {}
  const result = await addOrganization(
    props.organizationId,
    typedId.value ? { identifier: value } : { name: value },
  )
  busy.value = false
  if (result.error) {
    const message =
      result.status == 400
        ? (result.data?.identifier ?? result.data?.name)
        : undefined
    errors.value = message
      ? { text: [message].flat().join(" ") }
      : { detail: "The organization couldn't be added. Please try again." }
    return
  }
  emit("added", result.data as Entity)
}
</script>

<template>
  <form class="new-organization" @submit.prevent="add">
    <h4 :id="`${idPrefix}-title`">
      {{ title }} <small>Enter name, ROR ID or Wikidata ID</small>
    </h4>
    <div class="field">
      <InputText
        :id="`${idPrefix}-text`"
        :aria-labelledby="`${idPrefix}-title`"
        v-model="text"
        :invalid="!!errors.text"
        fluid
        @input="onInput"
      />
      <small v-if="errors.text" class="error">{{ errors.text }}</small>
      <small
        v-else-if="typedId && (lookupStatus != 'idle' || !currentLookup)"
        class="hint"
      >
        Looking up the {{ REGISTRY_LABELS[typedId.registry] }} ID…
      </small>
      <small v-else-if="currentLookup?.error" class="error">
        {{ currentLookup.error }}
      </small>
      <small v-else-if="currentLookup?.entity" class="hint lookup">
        Already in TSOSI: <strong>{{ currentLookup.entity.name }}</strong>
      </small>
      <small v-else-if="currentLookup?.record" class="hint lookup">
        {{ REGISTRY_LABELS[currentLookup.record.registry] }} record:
        <strong>{{
          currentLookup.record.name ?? currentLookup.record.identifier
        }}</strong>
        <template v-if="currentLookup.record.country">
          · {{ currentLookup.record.country }}
        </template>
      </small>
    </div>
    <Message v-if="errors.detail" severity="error">
      {{ errors.detail }}
    </Message>
    <div class="actions">
      <Button
        label="Cancel"
        severity="secondary"
        type="button"
        @click="emit('cancel')"
      />
      <Button
        :label="submitLabel"
        type="submit"
        :loading="busy"
        :disabled="!!typedId && !currentLookup"
      />
    </div>
  </form>
</template>

<style scoped>
.new-organization {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--p-neutral-300);
  border-radius: 6px;
  background: var(--p-neutral-50);
}

h4 {
  margin: 0;
}

h4 small {
  margin-left: 0.5rem;
  font-weight: normal;
  color: var(--p-neutral-600);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.error {
  color: var(--p-red-600);
}

.hint {
  color: var(--p-neutral-600);
}

.actions {
  display: flex;
  gap: 0.5rem;
}
</style>
