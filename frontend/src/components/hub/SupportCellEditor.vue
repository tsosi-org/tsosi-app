<script setup lang="ts">
import Button from "primevue/button"
import InputGroup from "primevue/inputgroup"
import InputText from "primevue/inputtext"
import Select from "primevue/select"
import { computed, onMounted, ref, watch } from "vue"

import EntityLinkDataAtom from "@/components/atoms/EntityLinkDataAtom.vue"
import SearchBar from "@/components/SearchBar.vue"
import {
  EDITOR_FIELD_ERRORS,
  parseAmountInput,
  type DeclarationErrors,
  type EditorField,
  type SupportDraft,
} from "@/singletons/hub-declarations"
import { recipientScope, scopeHighlight } from "@/singletons/hub-organizations"
import {
  getCurrencies,
  type Currency,
  type DeepReadonly,
  type Entity,
} from "@/singletons/ref-data"

/**
 * The input of an editable cell of the row being edited, in place of its
 * value. An organization (the beneficiary, or the intermediary) shows with a
 * button replacing it by the organization search, in the same place; a
 * beneficiary whose supports aren't public is highlighted. The
 * amount is typed, its currency picked next to it. The dates are typed in the panel under the
 * row (`SupportDates`). The cell shows that it's invalid; the panel lists the
 * errors.
 */

type OrganizationField = "agents" | "recipient"

const props = defineProps<{
  field: Exclude<EditorField, "date" | "currency">
  // The organization whose Hub it is
  organizationId: string
  errors: DeclarationErrors
}>()
const draft = defineModel<SupportDraft>("draft", { required: true })
const emit = defineEmits<{
  // Add an organization missing from TSOSI, in the panel under the row
  addOrganization: [field: OrganizationField, text: string]
  // The cell is being edited
  focus: []
}>()

const currencies = ref<DeepReadonly<Currency>[]>([])

onMounted(async () => {
  if (props.field == "amount") {
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

function highlight(organization: DeepReadonly<Entity>) {
  return props.field == "recipient"
    ? scopeHighlight(recipientScope(organization))
    : null
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
const currencyInvalid = computed(() =>
  EDITOR_FIELD_ERRORS.currency.some((key) => props.errors[key]),
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
            :class="highlight(organization)?.class"
            v-tooltip.bottom="highlight(organization)?.tooltip"
          >
            <EntityLinkDataAtom
              :data="{ entity: organization }"
              :dataField="entityField"
              noLink
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
          :addLabel="
            props.field == 'recipient'
              ? 'Add an infrastructure'
              : 'Add an intermediary'
          "
          @select="(entity) => pick(props.field as OrganizationField, entity)"
          @add="
            (text) =>
              emit('addOrganization', props.field as OrganizationField, text)
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

    <InputGroup v-else-if="props.field == 'amount'">
      <InputText
        :modelValue="draft.amountText"
        aria-label="Amount, all taxes included"
        inputmode="decimal"
        :invalid="invalid"
        @update:modelValue="onAmountInput"
      />
      <Select
        v-model="draft.currency"
        class="currency-select"
        aria-label="Currency"
        :options="currencies"
        optionLabel="id"
        optionValue="id"
        filter
        :invalid="currencyInvalid"
      >
        <template #option="{ option }">
          {{ option.id }} · {{ option.name }}
        </template>
      </Select>
    </InputGroup>
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

/* The amount takes the room the currency leaves */
.cell-editor :deep(.p-inputtext:not(.p-select-label)) {
  flex: 1;
  min-width: 0;
}

.currency-select {
  flex: none;
  width: 6.5rem;
}

/* The select's label inherits the page's line height, which inputs don't */
.cell-editor :deep(.p-select-label) {
  line-height: normal;
}
</style>
