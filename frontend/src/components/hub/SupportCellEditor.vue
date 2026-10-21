<script setup lang="ts">
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import Select from "primevue/select"
import { computed, onMounted, ref, watch } from "vue"

import EntityLinkDataAtom from "@/components/atoms/EntityLinkDataAtom.vue"
import ScopeTag from "@/components/hub/ScopeTag.vue"
import SearchBar from "@/components/SearchBar.vue"
import {
  EDITOR_FIELD_ERRORS,
  parseAmountInput,
  type DeclarationErrors,
  type EditorField,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import {
  addOrganization,
  recipientScope,
  type RegistryRecord,
} from "@/singletons/hub-organizations"
import {
  getCurrencies,
  type Currency,
  type DeepReadonly,
  type Entity,
} from "@/singletons/ref-data"

/**
 * The input of an editable cell of the row being edited, in place of its
 * value. An organization (the beneficiary, or the intermediary) shows with a
 * button replacing it by the organization search, in the same place. The
 * amount and currency are typed. The dates are typed in the panel under the
 * row (`SupportDates`). The cell shows that it's invalid; the panel lists the
 * errors.
 */

type OrganizationField = "agents" | "recipient"

const props = defineProps<{
  field: Exclude<EditorField, "date">
  // The organization whose Hub it is
  organizationId: string
  errors: DeclarationErrors
}>()
const draft = defineModel<SupportDraft>("draft", { required: true })
const emit = defineEmits<{
  // Add an organization from its name, in the panel under the row
  addOrganization: [field: OrganizationField, name: string]
  // The cell is being edited
  focus: []
  // An error of the cell not from the server, e.g. an organization that
  // couldn't be added
  error: [message: string]
}>()

const currencies = ref<DeepReadonly<Currency>[]>([])

onMounted(async () => {
  if (props.field == "currency") {
    currencies.value = Object.values((await getCurrencies()) ?? {}).sort(
      (a, b) => a.id.localeCompare(b.id),
    )
  }
})

// The entity shown like in the table, without the link to its page
const entityField = {
  id: "entity",
  title: "Organization",
  field: "entity",
  type: "entityLink" as const,
}

// The organizations of the cell
const organizations = computed<DeepReadonly<Entity>[]>(() => {
  if (props.field == "recipient") {
    return draft.value.recipient ? [draft.value.recipient] : []
  }
  return props.field == "agents" ? draft.value.agents : []
})

// The search replacing the organization, shown at once without one
const replacing = ref(false)
const searching = computed(
  () => replacing.value || organizations.value.length == 0,
)

// Replaced from elsewhere, e.g. added from its name in the panel under the
// row: shown
watch(
  () => organizations.value.map((o) => o.id).join(),
  () => (replacing.value = false),
)

function pick(field: OrganizationField, entity: DeepReadonly<Entity>) {
  if (field == "recipient") {
    draft.value.recipient = entity
  } else {
    draft.value.agents = [entity]
  }
  replacing.value = false
}

function clear() {
  draft.value.agents = []
  replacing.value = false
}

// An organization being added from its ROR or Wikidata record
const addingRecord = ref(false)

async function addRecord(field: OrganizationField, record: RegistryRecord) {
  addingRecord.value = true
  const result = await addOrganization(props.organizationId, {
    identifier: record.identifier,
  })
  addingRecord.value = false
  if (result.error) {
    const message = result.data?.identifier ?? result.data?.detail
    emit(
      "error",
      message
        ? [message].flat().join(" ")
        : "The organization couldn't be added. Please try again.",
    )
    return
  }
  pick(field, result.data as Entity)
}

// The amount as typed, committed at each keystroke when it's valid: with
// a `.` or a `,` for the decimals, whatever the member's convention
function onAmountInput(text: string | undefined) {
  draft.value.amountText = text ?? ""
  draft.value.amount = parseAmountInput(draft.value.amountText)?.amount ?? null
}

// Its errors, or an amount that isn't one, at once
const invalid = computed(
  () =>
    (props.field == "amount" &&
      parseAmountInput(draft.value.amountText) == null) ||
    EDITOR_FIELD_ERRORS[props.field].some((key) => props.errors[key]),
)
</script>

<template>
  <!-- The table's rows handle the clicks and keys (selection): not those
       of the inputs -->
  <div class="cell-editor" @click.stop @keydown.stop @focusin="emit('focus')">
    <template v-if="props.field == 'agents' || props.field == 'recipient'">
      <div v-if="!searching" class="organization">
        <div class="organization-values">
          <span
            v-for="organization of organizations"
            :key="organization.id"
            class="organization-value"
          >
            <EntityLinkDataAtom
              :data="{ entity: organization }"
              :dataField="entityField"
              noLink
            />
            <ScopeTag
              v-if="props.field == 'recipient'"
              :scope="recipientScope(organization)"
            />
          </span>
        </div>
        <Button
          v-tooltip.bottom="'Replace'"
          aria-label="Replace"
          severity="secondary"
          text
          size="small"
          @click="replacing = true"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'pen']" />
          </template>
        </Button>
        <Button
          v-if="props.field == 'agents'"
          v-tooltip.bottom="'No intermediary'"
          aria-label="No intermediary"
          severity="secondary"
          text
          size="small"
          @click="clear"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'xmark']" />
          </template>
        </Button>
      </div>
      <div v-else class="organization">
        <SearchBar
          hub
          :invalid="invalid"
          :autofocus="replacing"
          :placeHolder="
            props.field == 'recipient'
              ? 'Pick the beneficiary'
              : 'Pick the intermediary, if any'
          "
          @select="(entity) => pick(props.field as OrganizationField, entity)"
          @addRecord="
            (record) => addRecord(props.field as OrganizationField, record)
          "
          @add="
            (name) =>
              emit('addOrganization', props.field as OrganizationField, name)
          "
        />
        <Button
          v-if="replacing"
          v-tooltip.bottom="'Keep it'"
          aria-label="Keep it"
          severity="secondary"
          text
          size="small"
          @click="replacing = false"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'rotate-left']" />
          </template>
        </Button>
      </div>
    </template>

    <InputText
      v-else-if="props.field == 'amount'"
      :modelValue="draft.amountText"
      aria-label="Amount, all taxes included"
      inputmode="decimal"
      fluid
      :invalid="invalid"
      @update:modelValue="onAmountInput"
    />

    <Select
      v-else-if="props.field == 'currency'"
      v-model="draft.currency"
      aria-label="Currency"
      :options="currencies"
      optionLabel="id"
      optionValue="id"
      filter
      fluid
      :invalid="invalid"
    >
      <template #option="{ option }">
        {{ option.id }} · {{ option.name }}
      </template>
    </Select>

    <small v-if="addingRecord" class="hint">Adding the organization…</small>
  </div>
</template>

<style scoped>
.cell-editor {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 9rem;
  color: var(--p-text-color);
}

/* The value, or the search, with its buttons on the right */
.organization {
  display: flex;
  align-items: center;
  gap: 0.2rem;

  & > :first-child {
    flex: 1;
    min-width: 0;
  }
}

.organization-values {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.organization-value {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

/* The select's label inherits the page's line height, which inputs don't */
.cell-editor :deep(.p-select-label) {
  line-height: normal;
}

.hint {
  color: var(--p-neutral-500);
}
</style>
