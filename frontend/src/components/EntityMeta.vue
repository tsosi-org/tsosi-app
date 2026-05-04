<script setup lang="ts">
import Button from "primevue/button"
import Panel from "primevue/panel"
import { computed, onMounted, ref, watch, type Ref } from "vue"

import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"
import Image from "./atoms/ImageAtom.vue"

import ChipList, { type ChipConfig } from "@/components/atoms/ChipListAtom.vue"
import { isDesktop } from "@/composables/useMediaQuery"
import { type EntityDetails } from "@/singletons/ref-data"
import { formatDateWithPrecision, getCountryLabel } from "@/utils/data-utils"
import { getRorUrl, getWikidataUrl } from "@/utils/url-utils"

const props = defineProps<{
  entity: EntityDetails
}>()

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
  if (props.entity.country) {
    const countryName = getCountryLabel(props.entity.country)
    const countryChip: ChipConfig = {
      icon: ["fas", "location-dot"],
      label: countryName,
    }
    const legalEntityDesc =
      props.entity.infrastructure?.legal_entity_description
    if (legalEntityDesc) {
      countryChip.info = legalEntityDesc
    }
    headerChips.value.push(countryChip)
  }

  if (props.entity.date_inception) {
    headerChips.value.push({
      icon: ["fas", "calendar"],
      label: `Since ${props.entity.date_inception.getFullYear()}`,
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
  <div class="entity-meta" :class="{ desktop: isDesktop }">
    <section class="entity-header">
      <div class="entity-header__title">
        <div class="entity-title">
        <h1 >
          {{ props.entity.name }}
        </h1>
        </div>
        <ChipList
          :chips="headerChips"
          :center="!isDesktop"
          :style="{ justifyContent: 'center', marginTop: '1rem' }"
        />
      </div>

      <div
        class="entity-header__grid"
      >
        <div class="entity-header__logo">
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
          <div
            v-if="props.entity.description"
            v-html="props.entity.description"
          ></div>
          <div v-else-if="props.entity.wikipedia_extract">
            <p>
              {{ props.entity.wikipedia_extract }}
              <span class="wiki-disclaimer">
                <ExternalLinkAtom
                  :label="'Wikipedia'"
                  :href="props.entity.wikipedia_url!"
                /> -
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
              v-if="props.entity.website"
              :href="props.entity.website"
              rounded variant="outlined" as="a" target="_blank" rel="noopener"
            >
              <template #icon>
                <font-awesome-icon class="fa-icon" :icon="['fas', 'globe']" />
              </template>
            </Button>
            <Button
              v-if="props.entity.wikipedia_url"
              :href="props.entity.wikipedia_url"
              rounded variant="outlined" as="a" target="_blank" rel="noopener"
            >
              <img alt="Wikipedia logo" src="@/assets/img/wikipedia_icon.ico" />
            </Button>
            <Button
              v-if="rorIdentifier"
              :href="getRorUrl(rorIdentifier)"
              rounded variant="outlined" as="a" target="_blank" rel="noopener"
            >
              <template #default>
                <img alt="ROR logo" src="@/assets/img/ror_icon_rgb.svg" />
              </template>
            </Button>
            <Button
              v-if="wikidataIdentifier"
              :href="getWikidataUrl(wikidataIdentifier)"
              rounded variant="outlined" as="a" target="_blank" rel="noopener"
            >
              <img alt="Wikidata logo" src="@/assets/img/wikidata_icon.ico" />
            </Button>
            </div>
            <Button
            v-if="props.entity.infrastructure?.support_url"
            variant="outlined"  severity="secondary"
            as="a" target="_blank" rel="noopener"
            :href="props.entity.infrastructure.support_url"
            label="Find out how to support DOAJ"
            class="support_button icon-right"
          >
            <template #icon>
              <font-awesome-icon
                :icon="['fas', 'arrow-up-right-from-square']"
              />
            </template>
          </Button>
          </div>
          <div v-if="hasButtons" class="entity-header__buttons">
            <Button
              v-if="props.entity.is_partner"
              label="TSOSI"
              variant="outlined"
              as="div"
              v-tooltip.top="{ value: 'TSOSI provider. See the <a href=\'https://tsosi.org/pages/faq#data-provider\'>FAQ</a>.', escape: false, autoHide: false }"
            >
              <template #icon>
                <img src="/img/favicon-192x192.png" />
              </template>
            </Button>
            <Button
              v-if="props.entity.is_scoss"
              as="a" target="_blank" rel="noopener"
              href="https://scoss.org/how-it-works/current-funding-calls/"
              label="SCOSS"
              variant="outlined"
              v-tooltip.top="{ value: `Selected by <a target=\'_blank\' href=\'https://scoss.org/how-it-works/current-funding-calls\'>SCOSS</a> for the period ${props.entity.infrastructure?.date_scoss_start?.getFullYear()}-${props.entity.infrastructure?.date_scoss_end?.getFullYear()}.`, escape: false, autoHide: false }"
            >
              <template #icon>
                <img src="@/assets/img/scoss_icon.png" />
              </template>
            </Button>
            <Button
              v-if="props.entity.infrastructure?.posi_url"
              as="a" target="_blank" rel="noopener"
              :href="props.entity.infrastructure.posi_url"
              variant="outlined"
              label="POSI"
              v-tooltip.top="{ value: 'Adopter of the <a target=\'_blank\' href=\'https://openscholarlyinfrastructure.org/\'>POSI principles</a>.', escape: false, autoHide: false }"
            >
              <template #icon>
                <img src="@/assets/img/posi_icon.ico" />
              </template>
            </Button>
            <Button
              v-if="props.entity.is_barcelona"
              as="a" target="_blank" rel="noopener"
              href="https://barcelona-declaration.org/signatories/"
              variant="outlined"
              label="Barcelona Declaration"
              v-tooltip.top="{ value: 'Signatory of the <a target=\'_blank\' href=\'https://barcelona-declaration.org/\'>Barcelona Declaration</a>.', escape: false, autoHide: false }"
            >
              <template #icon>
                <img class="barcelona_icon" src="@/assets/img/barcelona_icon.jpg" />
              </template>
            </Button>
                    <Button
              v-if="props.entity.infrastructure?.infra_finder_url"
              as="a" target="_blank" rel="noopener"
              :href="props.entity.infrastructure?.infra_finder_url"
              variant="outlined"
              label="Infra Finder"
              v-tooltip.top="{ value: 'Included in <a target=\'_blank\' href=\'https://infrafinder.investinopen.org/solutions/\'>Infra Finder</a>.', escape: false, autoHide: false }"
            >
              <template #icon>
                <img src="@/assets/img/ioi_icon.ico" />
              </template>
            </Button>
          </div>
        </div>
        <!-- <div v-if="props.entity.is_partner">
            <img
              class="tsosi-partner"
              src="@/assets/img/tsosi_provider.svg"
            />
        </div> -->
      </div>
    </section>

    <section class="data-info">
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
            <li
              v-if="props.entity.is_recipient && !props.entity.is_partner"
              class="important-info"
            >
              The data below comes from TSOSI’s providers; they
              represent only a subset of this infrastructure's supporters.
            </li>
            <li>Each line of the table below shows a financial support.</li>
            <li>
              TSOSI's data comes from
              <RouterLink to="/pages/faq#data-provider"
                >its providers</RouterLink
              >.
            </li>
            <li v-if="isDoaj() || isDoab()">
              Most of the support amounts are hidden for DOAJ and DOAB:
              <RouterLink to="/pages/faq#amounts-hidden">see the FAQ</RouterLink
              >.
            </li>
            <li v-if="isDoaj() || isDoab()">
              DOAJ and DOAB data only start from 2021:
              <RouterLink to="/pages/faq#doaj-or-doab-page-missing-institution"
                >see the FAQ</RouterLink
              >.
            </li>
            <li v-if="props.entity.date_data_update">
              Last data update:
              {{
                formatDateWithPrecision(props.entity.date_data_update, "day")
              }}.
            </li>
          </ul>
        </div>
      </Panel>
    </section>
  </div>
</template>

<style scoped>
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
