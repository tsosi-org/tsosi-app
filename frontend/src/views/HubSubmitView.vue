<script setup lang="ts">
import Button from "primevue/button"
import Checkbox from "primevue/checkbox"
import { computed, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Message from "@/components/atoms/MessageAtom.vue"
import NotFound from "@/components/atoms/NotFound.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import Table, { type TableColumnProps } from "@/components/TableComponent.vue"
import {
  getDeclarations,
  getSubmissions,
  submitDeclarations,
  type Declaration,
  type DeclarationKind,
} from "@/singletons/hub-declarations"
import { recipientScope } from "@/singletons/hub-organizations"
import { session } from "@/singletons/hub-session"
import {
  getEntityPreview,
  getEntitySummary,
  getHubTransfers,
  getPublicationPreview,
  type DeepReadonly,
  type Entity,
  type EntityDetails,
  type HubTransfer,
  type PreviewTransfer,
} from "@/singletons/ref-data"
import { changeMetaTitle } from "@/utils/seo"
import { getHubEntityRef } from "@/utils/url-utils"
import {
  hiddenTransferColumns,
  transferColumns,
  transferDetailsButton,
} from "@/utils/transfer-table"

/**
 * Preview and submit the organization's changes not published yet: their
 * counts, its public page once they're published, as it will show, and the
 * submission, with the agreement to publish them under CC BY-SA 4.0.
 */
const route = useRoute()
const router = useRouter()

changeMetaTitle("Preview and submit · Data Contribution Hub")

const organization = ref<EntityDetails | null>(null)
// The TSOSI team on another organization's Hub
const readOnly = ref(false)
const loading = ref(true)
const loadError = ref(false)
// The drafts changed between the requests of the preview and of the
// declarations, e.g. by another member: the preview is reloaded
const changedSince = ref(false)
const transfers = ref<HubTransfer[]>([])
const drafts = ref<Declaration[]>([])
const entities = ref<Record<string, Entity>>({})
const waitingCount = ref(0)
const preview = ref<{
  transfers: PreviewTransfer[]
  changes: Record<string, string[]>
  declarationIds: number[]
  declarationsHash: string
} | null>(null)

const consent = ref(false)
const submitting = ref(false)
const submitError = ref<string | null>(null)

async function load(entityId: string) {
  loading.value = true
  loadError.value = false
  changedSince.value = false
  consent.value = false
  submitError.value = null
  const result = await getEntityPreview(entityId)
  const ref = result && getHubEntityRef(result.entity)
  if (ref && ref != entityId) {
    // The URL with its TSOSI ID
    router.replace({
      name: route.name!,
      params: { entityId: ref },
      query: route.query,
    })
    return
  }
  readOnly.value = session.member?.organization?.id != result?.entity.id
  // Infrastructures and consortia only edit their profile for now
  if (!result || (!readOnly.value && !session.member?.can_declare_supports)) {
    organization.value = null
    loading.value = false
    return
  }
  organization.value = result.entity
  const [transfersResult, declarationsResult, previewResult, submissions] =
    await Promise.all([
      getHubTransfers(result.entity),
      getDeclarations(entityId),
      getPublicationPreview(result.entity),
      getSubmissions(entityId),
    ])
  if (!transfersResult || !declarationsResult || !previewResult) {
    loadError.value = true
  } else {
    transfers.value = transfersResult.transfers
    // The drafts previewed, those submitted: all listed, or the preview is
    // reloaded
    const previewed = new Set(previewResult.declarationIds)
    drafts.value = declarationsResult.declarations.filter(
      (d) => d.status == "draft" && previewed.has(d.id),
    )
    changedSince.value = drafts.value.length != previewed.size
    entities.value = {
      ...transfersResult.entities,
      ...declarationsResult.entities,
    }
    preview.value = previewResult
    waitingCount.value = submissions?.length ?? 0
  }
  loading.value = false
}

watch(
  () => route.params.entityId as string | undefined,
  (entityId) => {
    if (entityId) {
      load(entityId)
    }
  },
  { immediate: true },
)

function getEntity(id: string | null): DeepReadonly<Entity> | undefined {
  return id ? (entities.value[id] ?? getEntitySummary(id)) : undefined
}

// Loaded, with the drafts previewed listed
const ready = computed(() => !loadError.value && !changedSince.value)

const transferById = computed(
  () => new Map(transfers.value.map((t) => [t.id, t])),
)

// The beneficiary of a change, with its declared values or the transfer's
function changeRecipient(
  declaration: Declaration,
): DeepReadonly<Entity> | undefined {
  if (["new", "edit"].includes(declaration.kind)) {
    return getEntity(declaration.recipient_id)
  }
  const transfer = transferById.value.get(declaration.transfer_id ?? "")
  return transfer?.recipient
}

const kindPlurals: Record<DeclarationKind, [string, string]> = {
  new: ["new support", "new supports"],
  confirmation: ["confirmation", "confirmations"],
  edit: ["edit", "edits"],
  removal: ["removal", "removals"],
  merge: ["merge", "merges"],
  not_duplicate: ["not a duplicate", "not duplicates"],
}

const counts = computed(() => {
  const result: { label: string; count: number }[] = []
  for (const kind of Object.keys(kindPlurals) as DeclarationKind[]) {
    const count = drafts.value.filter((d) => d.kind == kind).length
    if (count) {
      result.push({ count, label: kindPlurals[kind][count == 1 ? 0 : 1] })
    }
  }
  const newOrganizations = new Set(
    drafts.value
      .flatMap((d) => [d.recipient_id, ...d.agent_ids])
      .filter((id) => id && getEntity(id)?.is_new),
  ).size
  if (newOrganizations) {
    result.push({
      count: newOrganizations,
      label: newOrganizations == 1 ? "new organization" : "new organizations",
    })
  }
  return result
})

// The supports to beneficiaries not in scope: not on the public page
const notPublicCount = computed(
  () =>
    drafts.value.filter((d) => {
      const recipient = d.kind != "removal" && changeRecipient(d)
      return recipient && recipientScope(recipient) != "in_scope"
    }).length,
)

// The columns of the public page. The amounts declared in the Hub show in
// their own currency until converted by TSOSI, once published; the hidden
// ones, without their currency.
function previewColumns(): TableColumnProps[] {
  const columns = transferColumns()
  for (const id of ["amount", "currency"] as const) {
    const column = columns.find((c) => c.id == id)!
    const publicLabel = column.labelGetter!
    column.labelGetter = (row) => {
      if (row.amount_hidden) {
        return null
      }
      return row.unconverted ? row[id] : publicLabel(row)
    }
  }
  return columns
}

const previewTableProps = computed(() => {
  if (!preview.value || !organization.value) {
    return null
  }
  const rows = preview.value.transfers
  const hidden = hiddenTransferColumns(organization.value, rows)
  return {
    id: `${organization.value.id}-hub-preview`,
    data: rows,
    columns: previewColumns().filter((c) => !hidden.includes(c.id)),
    defaultSort: { sortField: "date_clc", sortOrder: -1 as const },
    rowUniqueId: "id",
    buttons: [transferDetailsButton],
    // Their page exists once published
    hideButtons: (row: Record<string, any>) =>
      !!preview.value?.changes[row.id]?.includes("new"),
    disableExport: true,
  }
})

function reload() {
  load(route.params.entityId as string)
}

function back() {
  router.push({
    name: "hub-home",
    params: { entityId: getHubEntityRef(organization.value!) },
  })
}

async function submit() {
  submitting.value = true
  submitError.value = null
  const result = await submitDeclarations(
    organization.value!.id,
    preview.value!,
  )
  submitting.value = false
  if (result.error) {
    // A message, or a list of messages for the validation errors
    const message = result.data?.detail ?? result.data?.consent
    submitError.value = message
      ? [message].flat().join(" ")
      : "The changes couldn't be submitted. Please try again."
    return
  }
  back()
}
</script>

<template>
  <Loader v-if="loading" width="150px"></Loader>
  <NotFound v-else-if="!organization"></NotFound>
  <div class="container" v-else>
    <div class="regular-content hub-submit">
      <div class="submit-header">
        <div class="submit-title">
          <RouterLink
            :to="{
              name: 'hub-home',
              params: { entityId: getHubEntityRef(organization) },
            }"
            class="back-link"
          >
            <font-awesome-icon :icon="['fas', 'arrow-left']" />
            Back to the supports of {{ organization.name }}
          </RouterLink>
          <h1>Preview and submit</h1>
          <template v-if="ready && drafts.length">
            <ul class="counts">
              <li v-for="item of counts" :key="item.label">
                <strong>{{ item.count }}</strong> {{ item.label }}
              </li>
            </ul>
            <p v-if="notPublicCount" class="hint">
              {{ notPublicCount }}
              {{ notPublicCount == 1 ? "change is" : "changes are" }} about
              infrastructures not in TSOSI's scope yet: their supports aren't on
              the public page until they are.
            </p>
            <p v-if="waitingCount" class="hint">
              The changes already waiting for approval aren't included.
            </p>
          </template>
        </div>
        <section
          v-if="!readOnly && ready && drafts.length"
          class="submit-box"
          aria-label="Submit"
        >
          <div class="consent">
            <Checkbox
              v-model="consent"
              inputId="hub-consent"
              binary
              class="consent-checkbox"
            />
            <label for="hub-consent">
              I confirm this data is accurate and agree to its publication on
              tsosi.org under the
              <a
                href="https://creativecommons.org/licenses/by-sa/4.0/"
                target="_blank"
                rel="noopener"
                >CC BY-SA 4.0 licence</a
              >.
            </label>
          </div>
          <div class="buttons">
            <Button
              label="Cancel"
              severity="secondary"
              variant="outlined"
              @click="back"
            />
            <Button
              label="Submit for review"
              :disabled="!consent"
              :loading="submitting"
              @click="submit"
            >
              <template #icon>
                <font-awesome-icon :icon="['fas', 'paper-plane']" />
              </template>
            </Button>
          </div>
          <Message v-if="submitError" severity="error">
            {{ submitError }}
          </Message>
        </section>
      </div>
      <Message v-if="readOnly">
        You're viewing this organization's changes as a TSOSI admin, in
        read-only mode.
      </Message>
      <Message v-if="loadError" severity="error">
        The preview couldn't be loaded. Please try again later.
      </Message>
      <Message v-else-if="changedSince" severity="warn">
        <div class="changed-since">
          The changes were modified while the preview was loading, e.g. by
          another member: reload it to see and submit them.
          <Button label="Reload" size="small" @click="reload" />
        </div>
      </Message>
      <p v-else-if="!drafts.length">There are no changes to submit.</p>
      <section v-else aria-labelledby="preview-title">
        <h2 id="preview-title">Preview of your public page</h2>
        <div class="preview-frame">
          <EntityMeta :entity="organization" />
          <Table v-if="previewTableProps" v-bind="previewTableProps" />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.hub-submit {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

h1,
h2 {
  margin: 0;
}

section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  align-self: flex-start;
}

.counts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;

  & li {
    padding: 0.3rem 0.8rem;
    border-radius: 6px;
    background: var(--p-neutral-100);
  }
}

.hint {
  margin: 0;
  color: var(--p-neutral-600);
}

/* The public page, framed */
.preview-frame {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--p-neutral-300);
  border-radius: 8px;
}

/* The title on the left, the submission on the right */
.submit-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem 2rem;
}

.submit-title {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.submit-title {
  flex: 1 1 20rem;
}

/* A card: the consent, then its buttons on the right */
.submit-box {
  flex: 0 1 28rem;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--p-neutral-300);
  border-radius: 8px;
  background: var(--p-content-background);
}

.consent {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  line-height: 1.5;

  & label {
    cursor: pointer;
  }
}

/* Centered on the label's first line */
.consent-checkbox {
  flex-shrink: 0;
  margin-top: calc((1.5em - var(--p-checkbox-height)) / 2);
}

.changed-since {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

.buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
