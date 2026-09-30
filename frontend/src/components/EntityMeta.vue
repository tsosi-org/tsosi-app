<script setup lang="ts">
import { devMode } from "@/singletons/devMode"
import Button from "primevue/button"
import Checkbox from "primevue/checkbox"
import InputNumber from "primevue/inputnumber"
import InputText from "primevue/inputtext"
import Message from "primevue/message"
import Panel from "primevue/panel"
import Select from "primevue/select"
import Textarea from "primevue/textarea"
import { computed, onMounted, ref, watch, type Ref } from "vue"

import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"
import Image from "./atoms/ImageAtom.vue"

import ChipList, { type ChipConfig } from "@/components/atoms/ChipListAtom.vue"
import { useEntityEdit } from "@/composables/useEntityEdit"
import { isDesktop } from "@/composables/useMediaQuery"
import { getCountries, type EntityDetails } from "@/singletons/ref-data"
import { formatDateWithPrecision, getCountryLabel } from "@/utils/data-utils"
import { getRorUrl, getWikidataUrl } from "@/utils/url-utils"

const props = defineProps<{
  entity: EntityDetails
  // Whether the user is allowed to edit the entity
  editable?: boolean
}>()

const emit = defineEmits<{
  saved: []
}>()

const editing = ref(false)
const editSaved = ref(false)
const {
  form,
  logoPreview,
  iconPreview,
  saving,
  globalError,
  showInfrastructure,
  reset: resetEdit,
  setLogo,
  setIcon,
  fieldError,
  save,
} = useEntityEdit(() => props.entity)

const lockedIdentifierInfo = "Existing identifiers can't be changed."

const countryOptions: Ref<Array<{ code: string; name: string }>> = ref([])

async function startEdit() {
  resetEdit()
  editSaved.value = false
  editing.value = true
  if (!countryOptions.value.length) {
    const countries = await getCountries()
    countryOptions.value = Object.values(countries ?? {})
      .map((c) => ({ code: c.code.toUpperCase(), name: c.name }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
}

async function saveEdit() {
  if (await save()) {
    editing.value = false
    editSaved.value = true
    emit("saved")
  }
}

function onLogoChange(event: Event) {
  setLogo((event.target as HTMLInputElement).files?.[0] ?? null)
}

function onIconChange(event: Event) {
  setIcon((event.target as HTMLInputElement).files?.[0] ?? null)
}

const logoWidth = computed(() => (isDesktop.value ? "225px" : "125px"))
const logoHeight = computed(() => (isDesktop.value ? "125px" : "125px"))
const isInfrastructure = computed(() => props.entity.infrastructure != null)
const rorIdentifier = computed(() => {
  const ids = props.entity.identifiers.filter((id) => id.registry == "ror")
  if (ids.length > 0) {
    return ids[0].value
  }
  return null
})
const wikidataIdentifier = computed(() => {
  const ids = props.entity.identifiers.filter((id) => id.registry == "wikidata")
  if (ids.length > 0) {
    return ids[0].value
  }
  return null
})

const headerChips: Ref<Array<ChipConfig>> = ref([])
const bottomButtons: Ref<Array<any>> = ref([])

watch(() => props.entity, loadChips)
onMounted(() => loadChips())

const hasButtons = computed(() => {
  return (
    props.entity.is_partner ||
    props.entity.is_scoss ||
    props.entity.infrastructure?.posi_url ||
    props.entity.is_barcelona ||
    props.entity.infrastructure?.infra_finder_url
  )
})

function loadChips() {
  headerChips.value = []
  if (props.entity.country) {
    const countryName = getCountryLabel(props.entity.country)
    const countryChip: ChipConfig = {
      icon: ["fas", "location-dot"],
      label: countryName,
    }
    const legalEntityDesc =
      props.entity.is_recipient &&
      (wikidataIdentifier ||
        props.entity.infrastructure?.legal_entity_wikidata_id)
        ? `The legal entity is located in ${getCountryLabel(props.entity.country)}, see<a href=\"https://www.wikidata.org/wiki/${wikidataIdentifier.value || props.entity.infrastructure?.legal_entity_wikidata_id}\" rel=\"noopener noreferrer\" target=\"_blank\" class=\"wikidata-inline-link\">wikidata</a>`
        : null
    if (legalEntityDesc) {
      countryChip.info = legalEntityDesc
    }
    headerChips.value.push(countryChip)
  }

  if (props.entity.date_inception) {
    headerChips.value.push({
      icon: ["fas", "calendar"],
      label: `Since ${props.entity.date_inception.getUTCFullYear()}`,
    })
  }
}

function isDoaj(): boolean {
  return props.entity.identifiers.some(
    (val) => val.registry == "ror" && val.value == "05amyt365",
  )
}

function isDoab(): boolean {
  return props.entity.identifiers.some(
    (val) => val.registry == "_custom" && val.value == "doab_oapen",
  )
}
</script>

<template>
  <div
    class="entity-meta"
    :class="{ desktop: isDesktop, editable: props.editable }"
  >
    <div v-if="props.editable" class="edit-bar">
      <div class="edit-bar__buttons">
        <Button
          v-if="!editing"
          label="Edit"
          severity="secondary"
          @click="startEdit"
        >
          <template #icon>
            <font-awesome-icon :icon="['fas', 'pen']" />
          </template>
        </Button>
        <template v-else>
          <Button
            label="Cancel"
            severity="secondary"
            variant="outlined"
            :disabled="saving"
            @click="editing = false"
          />
          <Button label="Save" :loading="saving" @click="saveEdit" />
        </template>
      </div>
      <Message
        v-if="editSaved"
        severity="success"
        closable
        @close="editSaved = false"
      >
        Your changes have been saved. Some data may take a few minutes to be
        fully updated.
      </Message>
      <Message v-if="editing && globalError" severity="error">
        {{ globalError }}
      </Message>
    </div>

    <section class="entity-header" :class="{ editing }">
      <div class="entity-header__title">
        <div class="entity-title">
          <h1 v-if="!editing">
            {{ props.entity.name }}
          </h1>
          <div v-else class="edit-title">
            <h1>
              <InputText
                v-model="form.name"
                class="title-input"
                aria-label="Name"
                placeholder="Name"
                maxlength="512"
                required
              />
            </h1>
            <small class="edit-error" v-if="fieldError('name')">
              {{ fieldError("name") }}
            </small>
            <InputText
              v-model="form.short_name"
              class="short-name-input"
              size="small"
              aria-label="Short name"
              placeholder="Short name"
              maxlength="128"
            />
            <small class="edit-error" v-if="fieldError('short_name')">
              {{ fieldError("short_name") }}
            </small>
          </div>
        </div>
        <ChipList
          v-if="!editing"
          :chips="headerChips"
          :center="!isDesktop"
          :style="{ justifyContent: 'center', marginTop: '1rem' }"
        />
        <div v-else class="edit-chips">
          <div class="edit-chip">
            <font-awesome-icon :icon="['fas', 'location-dot']" />
            <Select
              v-model="form.country"
              :options="countryOptions"
              option-label="name"
              option-value="code"
              filter
              size="small"
              aria-label="Country"
              placeholder="Country"
            />
          </div>
          <div class="edit-chip">
            <font-awesome-icon :icon="['fas', 'calendar']" />
            <span>Since</span>
            <InputNumber
              v-model="form.date_inception"
              :use-grouping="false"
              :min="1000"
              :max="2100"
              size="small"
              class="year-input"
              aria-label="Creation year"
              placeholder="Year"
            />
          </div>
          <small
            class="edit-error"
            v-if="fieldError('country') || fieldError('date_inception')"
          >
            {{ fieldError("country") }} {{ fieldError("date_inception") }}
          </small>
        </div>
      </div>

      <div class="entity-header__grid">
        <div class="entity-header__logo" v-if="editing">
          <label
            class="logo-edit"
            :class="{ empty: !logoPreview }"
            :style="{ width: logoWidth, height: logoHeight }"
          >
            <Image
              :key="logoPreview"
              style="display: inline-block"
              :src="logoPreview"
              :width="logoWidth"
              :height="logoHeight"
              :center="true"
              :container-padding="'5px'"
            />
            <span class="logo-overlay">
              <font-awesome-icon :icon="['fas', 'pen']" />
              {{ logoPreview ? "Change logo" : "Add a logo" }}
            </span>
            <input
              type="file"
              class="visually-hidden"
              accept="image/png,image/jpeg,image/webp"
              aria-label="Logo"
              @change="onLogoChange"
            />
          </label>
          <small class="edit-error logo-error" v-if="fieldError('logo')">
            {{ fieldError("logo") }}
          </small>
          <div class="icon-edit-row">
            <label
              class="logo-edit icon-edit"
              :class="{ empty: !iconPreview }"
              title="Icon"
            >
              <Image
                :key="iconPreview"
                :src="iconPreview"
                width="48px"
                height="48px"
                :center="true"
                :container-padding="'3px'"
              />
              <span class="logo-overlay">
                <font-awesome-icon :icon="['fas', 'pen']" />
              </span>
              <input
                type="file"
                class="visually-hidden"
                accept="image/png,image/jpeg,image/webp,image/x-icon"
                aria-label="Icon"
                @change="onIconChange"
              />
            </label>
          </div>
          <small class="edit-error logo-error" v-if="fieldError('icon')">
            {{ fieldError("icon") }}
          </small>
        </div>
        <div class="entity-header__logo" v-else>
          <Image
            style="display: inline-block"
            :src="props.entity?.logo"
            :width="logoWidth"
            :height="logoHeight"
            :center="true"
            :container-padding="'5px'"
          />
          <div
            v-if="!props.entity.logo"
            :style="`margin-top: ${isDesktop ? '-10px' : '-30px'};`"
          >
            <span :style="`display: inline-block; max-width: 125px;`">
              Logo not found, see
              <RouterLink :to="'/pages/faq#add-logo'">how to add it</RouterLink>
            </span>
          </div>
        </div>

        <div class="entiy-header__desc">
          <div v-if="editing" class="edit-description">
            <Textarea
              v-model="form.description"
              auto-resize
              rows="4"
              maxlength="5000"
              aria-label="Description"
              placeholder="Description (leave empty to use the Wikipedia extract)"
            />
            <small class="edit-error" v-if="fieldError('description')">
              {{ fieldError("description") }}
            </small>
          </div>
          <div
            v-else-if="props.entity.description"
            v-html="props.entity.description"
          ></div>
          <div v-else-if="props.entity.wikipedia_extract">
            <p>
              {{ props.entity.wikipedia_extract }}
              <span class="wiki-disclaimer">
                <ExternalLinkAtom
                  :label="'Wikipedia'"
                  :href="props.entity.wikipedia_url!"
                />
                -
                <ExternalLinkAtom
                  :label="'CC-BY-SA'"
                  :href="'https://en.wikipedia.org/wiki/Wikipedia:Text_of_the_Creative_Commons_Attribution-ShareAlike_4.0_International_License'"
                />
              </span>
            </p>
          </div>
          <div v-else>
            TSOSI relies on Wikidata and Wikipedia to obtain logos and
            descriptions of entities. Unfortunately, no Wikipedia description
            has been found for this entity so far. Please see
            <RouterLink :to="'/pages/faq#add-wiki-description'"
              >how to improve this </RouterLink
            >.
          </div>
          <div class="entity-header__links">
            <div class="entity-header__links_circles">
              <Button
                v-if="!editing && props.entity.website"
                :href="props.entity.website"
                rounded
                variant="outlined"
                as="a"
                target="_blank"
                rel="noopener"
              >
                <template #icon>
                  <font-awesome-icon class="fa-icon" :icon="['fas', 'globe']" />
                </template>
              </Button>
              <Button
                v-if="!editing && props.entity.wikipedia_url"
                :href="props.entity.wikipedia_url"
                rounded
                variant="outlined"
                as="a"
                target="_blank"
                rel="noopener"
              >
                <img
                  alt="Wikipedia logo"
                  src="@/assets/img/wikipedia_icon.ico"
                />
              </Button>
              <template v-if="editing">
                <div class="link-edit url">
                  <span class="link-edit__icon">
                    <font-awesome-icon
                      class="fa-icon"
                      :icon="['fas', 'globe']"
                    />
                  </span>
                  <InputText
                    v-model="form.website"
                    type="url"
                    size="small"
                    aria-label="Website URL"
                    placeholder="Website URL"
                  />
                  <small class="edit-error" v-if="fieldError('website')">
                    {{ fieldError("website") }}
                  </small>
                </div>
                <div class="link-edit url">
                  <span class="link-edit__icon">
                    <img
                      alt="Wikipedia logo"
                      src="@/assets/img/wikipedia_icon.ico"
                    />
                  </span>
                  <InputText
                    v-model="form.wikipedia_url"
                    type="url"
                    size="small"
                    aria-label="Wikipedia page URL"
                    placeholder="Wikipedia page URL"
                  />
                  <small class="edit-error" v-if="fieldError('wikipedia_url')">
                    {{ fieldError("wikipedia_url") }}
                  </small>
                </div>
                <div class="link-edit">
                  <span class="link-edit__icon">
                    <img alt="ROR logo" src="@/assets/img/ror_icon_rgb.svg" />
                  </span>
                  <InputText
                    v-model="form.ror"
                    size="small"
                    aria-label="ROR ID"
                    placeholder="ROR ID"
                    :disabled="rorIdentifier != null"
                    :title="rorIdentifier ? lockedIdentifierInfo : undefined"
                  />
                  <small
                    class="edit-error"
                    v-if="fieldError('identifiers.ror')"
                  >
                    {{ fieldError("identifiers.ror") }}
                  </small>
                </div>
                <div class="link-edit">
                  <span class="link-edit__icon">
                    <img
                      alt="Wikidata logo"
                      src="@/assets/img/wikidata_icon.ico"
                    />
                  </span>
                  <InputText
                    v-model="form.wikidata"
                    size="small"
                    aria-label="Wikidata ID"
                    placeholder="Wikidata ID"
                    :disabled="wikidataIdentifier != null"
                    :title="
                      wikidataIdentifier ? lockedIdentifierInfo : undefined
                    "
                  />
                  <small
                    class="edit-error"
                    v-if="fieldError('identifiers.wikidata')"
                  >
                    {{ fieldError("identifiers.wikidata") }}
                  </small>
                </div>
              </template>
              <Button
                v-if="!editing && rorIdentifier"
                :href="getRorUrl(rorIdentifier)"
                rounded
                variant="outlined"
                as="a"
                target="_blank"
                rel="noopener"
              >
                <template #default>
                  <img alt="ROR logo" src="@/assets/img/ror_icon_rgb.svg" />
                </template>
              </Button>
              <Button
                v-if="!editing && wikidataIdentifier"
                :href="getWikidataUrl(wikidataIdentifier)"
                rounded
                variant="outlined"
                as="a"
                target="_blank"
                rel="noopener"
              >
                <img alt="Wikidata logo" src="@/assets/img/wikidata_icon.ico" />
              </Button>
            </div>
            <div v-if="editing && showInfrastructure" class="badge-edit">
              <span>Find out how to support</span>
              <font-awesome-icon
                :icon="['fas', 'arrow-up-right-from-square']"
              />
              <InputText
                v-model="form.support_url"
                type="url"
                size="small"
                aria-label="Support page URL"
                placeholder="https://..."
              />
              <small
                class="edit-error"
                v-if="fieldError('infrastructure.support_url')"
              >
                {{ fieldError("infrastructure.support_url") }}
              </small>
            </div>
            <Button
              v-else-if="!editing && props.entity.infrastructure?.support_url"
              severity="secondary"
              variant="outlined"
              as="a"
              target="_blank"
              rel="noopener"
              :href="props.entity.infrastructure.support_url"
              label="Find out how to support"
              class="support_button icon-right"
            >
              <template #icon>
                <font-awesome-icon
                  :icon="['fas', 'arrow-up-right-from-square']"
                />
              </template>
            </Button>
          </div>
          <div v-if="editing" class="entity-header__buttons">
            <div v-if="props.entity.is_partner" class="badge-edit">
              <img src="/img/favicon-192x192.png" />
              <span>TSOSI provider</span>
            </div>
            <div
              v-if="showInfrastructure"
              class="badge-edit"
              :class="{ inactive: !form.date_scoss_start }"
            >
              <img src="@/assets/img/scoss_icon.png" />
              <span>SCOSS</span>
              <InputNumber
                v-model="form.date_scoss_start"
                :use-grouping="false"
                :min="1000"
                :max="2100"
                size="small"
                class="year-input"
                aria-label="SCOSS selection start year"
                placeholder="Year"
              />
              <span>to</span>
              <InputNumber
                v-model="form.date_scoss_end"
                :use-grouping="false"
                :min="1000"
                :max="2100"
                size="small"
                class="year-input"
                aria-label="SCOSS selection end year"
                placeholder="Year"
              />
              <small
                class="edit-error"
                v-if="fieldError('infrastructure.non_field_errors')"
              >
                {{ fieldError("infrastructure.non_field_errors") }}
              </small>
            </div>
            <div
              v-if="showInfrastructure"
              class="badge-edit"
              :class="{ inactive: !form.posi_url }"
            >
              <img src="@/assets/img/posi_icon.ico" />
              <span>POSI</span>
              <InputText
                v-model="form.posi_url"
                type="url"
                size="small"
                aria-label="POSI statement URL"
                placeholder="https://..."
              />
              <small
                class="edit-error"
                v-if="fieldError('infrastructure.posi_url')"
              >
                {{ fieldError("infrastructure.posi_url") }}
              </small>
            </div>
            <label class="badge-edit" :class="{ inactive: !form.is_barcelona }">
              <Checkbox v-model="form.is_barcelona" binary />
              <img
                class="barcelona_icon"
                src="@/assets/img/barcelona_icon.jpg"
              />
              <span>Barcelona Declaration</span>
            </label>
            <div
              v-if="showInfrastructure"
              class="badge-edit"
              :class="{ inactive: !form.infra_finder_url }"
            >
              <img src="@/assets/img/ioi_icon.ico" />
              <span>Infra Finder</span>
              <InputText
                v-model="form.infra_finder_url"
                type="url"
                size="small"
                aria-label="Infra Finder URL"
                placeholder="https://..."
              />
              <small
                class="edit-error"
                v-if="fieldError('infrastructure.infra_finder_url')"
              >
                {{ fieldError("infrastructure.infra_finder_url") }}
              </small>
            </div>
          </div>
          <div v-else-if="hasButtons" class="entity-header__buttons">
            <Button
              v-if="props.entity.is_partner"
              label="TSOSI provider"
              variant="outlined"
              as="div"
              v-tooltip.top="{
                value:
                  'TSOSI\'s data provider (see the <a href=\'/pages/faq#data-provider\'>FAQ</a>)',
                escape: false,
                autoHide: false,
              }"
            >
              <template #icon>
                <img src="/img/favicon-192x192.png" />
              </template>
            </Button>
            <Button
              v-if="props.entity.is_scoss"
              as="a"
              target="_blank"
              rel="noopener"
              href="https://scoss.org/how-it-works/current-funding-calls/"
              label="SCOSS"
              variant="outlined"
              v-tooltip.top="{
                value: `Selected by <a target=\'_blank\' href=\'https://scoss.org/how-it-works/current-funding-calls\'>SCOSS</a> for the period ${props.entity.infrastructure?.date_scoss_start?.getUTCFullYear()}-${props.entity.infrastructure?.date_scoss_end?.getUTCFullYear()}`,
                escape: false,
                autoHide: false,
              }"
            >
              <template #icon>
                <img src="@/assets/img/scoss_icon.png" />
              </template>
            </Button>
            <Button
              v-if="props.entity.infrastructure?.posi_url"
              as="a"
              target="_blank"
              rel="noopener"
              :href="props.entity.infrastructure.posi_url"
              variant="outlined"
              label="POSI"
              v-tooltip.top="{
                value:
                  'Adopter of the <a target=\'_blank\' href=\'https://openscholarlyinfrastructure.org/\'>POSI principles</a>',
                escape: false,
                autoHide: false,
              }"
            >
              <template #icon>
                <img src="@/assets/img/posi_icon.ico" />
              </template>
            </Button>
            <Button
              v-if="props.entity.is_barcelona"
              as="a"
              target="_blank"
              rel="noopener"
              href="https://barcelona-declaration.org/signatories/"
              variant="outlined"
              label="Barcelona Declaration"
              v-tooltip.top="{
                value:
                  (props.entity.is_recipient ? 'Supporter' : 'Signatory') +
                  ' of the <a target=\'_blank\' href=\'https://barcelona-declaration.org/\'>Barcelona Declaration</a>',
                escape: false,
                autoHide: false,
              }"
            >
              <template #icon>
                <img
                  class="barcelona_icon"
                  src="@/assets/img/barcelona_icon.jpg"
                />
              </template>
            </Button>
            <Button
              v-if="props.entity.infrastructure?.infra_finder_url"
              as="a"
              target="_blank"
              rel="noopener"
              :href="props.entity.infrastructure?.infra_finder_url"
              variant="outlined"
              label="Infra Finder"
              v-tooltip.top="{
                value:
                  'Included in <a target=\'_blank\' href=\'https://infrafinder.investinopen.org/solutions/\'>Infra Finder</a>',
                escape: false,
                autoHide: false,
              }"
            >
              <template #icon>
                <img src="@/assets/img/ioi_icon.ico" />
              </template>
            </Button>
          </div>
        </div>
      </div>
    </section>

    <section class="data-info" v-if="!devMode">
      <Panel
        toggleable
        class="info-box"
        :dt="{ border: 'inherit', borderRadius: 'inherit' }"
      >
        <template #header>
          <h2 class="info-box-header">To consider before reading the data</h2>
        </template>
        <div class="info-box-content">
          <ul>
            <li>Each line of the table below shows a financial support</li>
            <li>
              TSOSI's data comes from
              <RouterLink to="/pages/faq#data-provider"
                >its providers</RouterLink
              >
            </li>
            <li v-if="!props.entity.is_partner">
              {{ props.entity.name }} is
              <strong>not yet a TSOSI data provider</strong>, the data below
              might not cover all of their supports
            </li>
            <li v-if="isDoaj() || isDoab()">
              DOAJ and DOAB data only start from 2021:
              <RouterLink to="/pages/faq#doaj-or-doab-page-missing-institution"
                >see the FAQ</RouterLink
              >
            </li>
            <li v-if="props.entity.date_data_update">
              Last data update:
              {{
                formatDateWithPrecision(props.entity.date_data_update, "day")
              }}
            </li>
          </ul>
        </div>
      </Panel>
    </section>
  </div>
</template>

<style scoped>
/* The edit bar floats over the header so that the content doesn't move */
.entity-meta.editable {
  position: relative;
}

.edit-bar {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5em;
  margin-top: 1em;
}

.entity-meta.desktop .edit-bar {
  position: absolute;
  top: 0;
  right: 0;
  margin: 0;
  z-index: 3;
}

.edit-bar__buttons {
  display: flex;
  gap: 0.5em;
}

.edit-bar .p-message {
  max-width: 24rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Keep the centered title clear from the edit bar */
.entity-meta.desktop.editable .entity-header__title {
  padding-inline: 10rem;
}

.year-input :deep(input) {
  width: 5.5rem;
}

.edit-error {
  color: var(--p-red-600);
  flex-basis: 100%;
}

.edit-help {
  color: var(--p-gray-500);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.edit-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.edit-title h1 {
  width: 100%;
}

/* Same style as the other inputs, with the size of the title */
.title-input {
  font: inherit;
  color: inherit;
  text-align: center;
  width: 100%;
  padding: 0 0.3em;
  border-radius: 8px;
}

.short-name-input {
  text-align: center;
}

.edit-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  column-gap: 2rem;
  row-gap: 1rem;
  margin-top: 1rem;
  text-align: center;
}

.edit-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem 0.25rem 1rem;
  border-radius: var(--p-chip-border-radius);
  background: var(--p-chip-background);
  color: var(--p-chip-color);
}

.edit-chip .p-select {
  min-width: 14rem;
  text-align: left;
}

.logo-edit {
  position: relative;
  display: inline-block;
  cursor: pointer;
  border-radius: 8px;

  /* Always visible border, drawn over the image without changing its size */
  &::after {
    content: "";
    position: absolute;
    inset: 0;
    border: 2px dashed var(--p-primary-color);
    border-radius: 8px;
    pointer-events: none;
  }
}

.logo-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5em;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  color: var(--p-primary-color);
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s ease-out;
}

.logo-edit:hover .logo-overlay,
.logo-edit:focus-within .logo-overlay,
.logo-edit.empty .logo-overlay {
  opacity: 1;
}

.icon-edit-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6em;
  margin-top: 0.8em;
  color: var(--p-gray-500);
}

.icon-edit {
  width: 48px;
  height: 48px;
}

.icon-edit::after {
  border-width: 1px;
}

.logo-error {
  display: block;
  max-width: v-bind(logoWidth);
}

.edit-description {
  display: flex;
  flex-direction: column;
  gap: 0.3em;

  & textarea {
    width: 100%;
  }
}

.link-edit {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  max-width: 13rem;

  &.url {
    max-width: 17rem;
  }
}

.link-edit__icon {
  display: inline-flex;
  padding: 0.5rem;
  border: 1px solid var(--p-button-outlined-primary-border-color);
  border-radius: 50%;

  & img {
    height: 1.5em;
    width: 1.5em;
  }
}

.link-edit .p-inputtext {
  width: 8rem;
}

.link-edit.url .p-inputtext {
  width: 12rem;
}

.badge-edit {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.9rem;
  border: 2px solid var(--p-button-outlined-primary-border-color);
  border-radius: var(--p-button-border-radius);

  & img {
    height: 1.5em;
    width: 1.5em;
  }

  & .barcelona_icon {
    border-radius: 2px;
    height: 1.4em;
  }

  &.inactive > img,
  &.inactive > span {
    opacity: 0.5;
  }
}

label.badge-edit {
  cursor: pointer;
}

.entity-header.editing .entity-header__links {
  flex-wrap: wrap;
  align-items: center;
}

.entity-header.editing .entity-header__links_circles {
  flex-wrap: wrap;
  align-items: center;
}

.entity-meta > * {
  margin-bottom: min(2em, 4vh);
}

.p-button img {
  height: 1.5em;
  width: 1.5em;
}

.p-button .barcelona_icon {
  border-radius: 2px;
  height: 1.4em;
}

.p-button {
  text-decoration: none;
}

div.p-button {
  cursor: reset;
}

div.p-button:hover {
  background-color: transparent;
}

.entity-header__grid {
  display: flex;
  flex-direction: row;
  gap: 2em;
  margin: 1em 0;
}

.entiy-header__desc {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1em;
}

.entiy-header__desc p {
  margin: 0;
}

.entity-header__links {
  display: flex;
  flex-direction: row;
  gap: 0.5em;
}

.entity-header__links_circles {
  display: flex;
  flex-direction: row;
  gap: 0.5rem;
  margin-right: 20px;
}

.entity-header__links .p-button {
  padding: 0.5rem;
}

.entity-header__logo {
  text-align: center;
}

.entity-header__logo .p-button {
  margin-top: 1rem;
}

.entity-header__buttons .p-button {
  border-width: 2px;
}

.entity-header__title {
  position: relative;
  text-align: center;
  flex-direction: column;
  gap: 1em;
  z-index: 2;

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    height: 100%;
    width: 100%;
    background-color: rgba(255, 255, 255, 0.8);
    /* Black with 50% transparency */
    z-index: -1;
    /* Ensure overlay is on top of the image */
  }
}

.entity-title {
  display: flex;
  align-items: center;
  justify-content: center;
}

.entity-title h1 {
  text-transform: initial;
  position: relative;
  top: 3px;
  font-size: 3rem;
  line-height: 1.25;
}

.tsosi-badge {
  margin-left: 20px;
  height: 35px;
}

.wiki-disclaimer {
  font-size: 0.9em;
  color: var(--p-gray-500);
  text-wrap: nowrap;

  a {
    color: inherit;
  }
}

.entity-header__buttons {
  margin-top: 2.2em;
  display: flex;
  gap: 10px;
  justify-content: start;
  flex-wrap: wrap;
}

.p-divider {
  margin: 0;
}

.entity-header__buttons .p-button:deep(span) {
  color: black;
}

.entity-header__desc__support {
  display: block;
  width: fit-content;
  text-decoration: unset;
  padding: 0.6rem 1.25rem;
  background-color: var(--p-surface-100);
  border-radius: 8px;
  transition: all 0.2s ease-out;
  text-align: center;

  &:hover,
  &:focus-visible {
    background-color: var(--p-surface-200);
  }
}

.important-info {
  background-color: var(--p-yellow-100);
  width: fit-content;
}

.icon-right.p-button {
  flex-direction: row-reverse;
}

@media (max-width: 500px) {
  .entity-header__grid {
    flex-direction: column;
    align-items: center;
  }

  .entity-header__links {
    flex-direction: column;
  }

  .entity-header__buttons {
    flex-direction: column;
    justify-content: center;
    margin-top: 0em;
  }
}
</style>
