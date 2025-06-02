<script setup lang="ts">
import { computed, watch, ref, type Ref, onMounted } from "vue"
import { type EntityDetails } from "@/singletons/ref-data"
import Image from "./atoms/ImageAtom.vue"
import { getRorUrl, getWikidataUrl } from "@/utils/url-utils"
import { isDesktop } from "@/composables/useMediaQuery"
import { getCountryLabel } from "@/utils/data-utils"
import InfrastructureInfoBox from "@/components/InfrastructureInfoBox.vue"
import EmitterInfoBox from "@/components/EmitterInfoBox.vue"
import ChipList, { type ChipConfig } from "@/components/atoms/ChipListAtom.vue"
import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"

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

const hasLinks = computed(
  () =>
    (props.entity.website || rorIdentifier.value || wikidataIdentifier.value) !=
    null,
)

const headerChips: Ref<Array<ChipConfig>> = ref([])
const bottomButtons: Ref<Array<any>> = ref([])

watch(() => props.entity, loadChips)
onMounted(() => loadChips())

function loadChips() {
  if (props.entity.country) {
    const countryName = getCountryLabel(props.entity.country)
    const countryChip: ChipConfig = {
      icon: "location-dot",
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
      icon: "calendar",
      label: `Since ${props.entity.date_inception.getFullYear()}`,
    })
  }

  // Infrastructure specific chips
  if (props.entity.infrastructure) {
    if (props.entity.infrastructure.posi_url) {
      bottomButtons.value.push({
        // icon: "arrow-up-right-from-square",
        label: "Committed to POSI",
        link: props.entity.infrastructure.posi_url,
      })
    }
    if (props.entity.infrastructure.infra_finder_url) {
      bottomButtons.value.push({
        // icon: "arrow-up-right-from-square",
        label: "Included in Infra Finder",
        link: props.entity.infrastructure.infra_finder_url,
      })
    }
    if (
      props.entity.infrastructure?.date_scoss_start &&
      props.entity.infrastructure?.date_scoss_end
    ) {
      const dateStart =
        props.entity.infrastructure.date_scoss_start.getFullYear()
      const dateEnd = props.entity.infrastructure.date_scoss_end.getFullYear()
      bottomButtons.value.push({
        // icon: "square-check",
        label: `SCOSS selected for ${dateStart}-${dateEnd}`,
        link: "https://scoss.org/how-it-works/current-funding-calls/",
      })
    }

    if (props.entity.infrastructure.support_url) {
      bottomButtons.value.push({
        label: "SUPPORT",
        link: props.entity.infrastructure.support_url,
        inverse: true,
      })
    }
  }
}

function breakdownDisclaimer(): boolean {
  return props.entity.identifiers.some(
    (val) => val.registry == "ror" && val.value == "05amyt365",
  )
}
</script>

<template>
  <div class="entity-meta" :class="{ desktop: isDesktop }">
    <section class="entity-header">
      <div class="entity-header__title">
        <h1 class="entity-title">
          {{ props.entity.name }}
        </h1>
        <ChipList
          :chips="headerChips"
          :center="!isDesktop"
          :style="{ justifyContent: 'center', marginTop: '1rem' }"
        />
      </div>

      <div
        class="entity-header__grid"
        :class="{ 'three-columns': hasLinks && !isInfrastructure }"
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
          <!--
            Description (manual) takes precedence on automatically
            fetched Wikipedia sumamry
          -->
          <div v-if="props.entity.description">
            <p>
              {{ props.entity.description }}
            </p>
          </div>
          <div v-else-if="props.entity.wikipedia_extract">
            <p>
              {{ props.entity.wikipedia_extract }}
            </p>
            <p>
              <span class="wiki-disclaimer">
                From
                <ExternalLinkAtom
                  :label="'Wikipedia'"
                  :href="props.entity.wikipedia_url!"
                />
                licensed
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
        </div>

        <div
          v-if="props.entity.infrastructure == null && hasLinks"
          class="entity-header__links"
        >
          <ExternalLinkAtom
            v-if="props.entity.website"
            :href="props.entity.website"
            class="entity-icon-link"
          >
            <template #default>
              <font-awesome-icon class="fa-icon" icon="globe" />
              Website
            </template>
          </ExternalLinkAtom>
          <ExternalLinkAtom
            v-if="rorIdentifier"
            :href="getRorUrl(rorIdentifier)"
            class="entity-icon-link"
          >
            <template #default>
              <img alt="ROR logo" src="@/assets/img/ror_icon_rgb.svg" />
              ROR
            </template>
          </ExternalLinkAtom>
          <ExternalLinkAtom
            v-if="wikidataIdentifier"
            :href="getWikidataUrl(wikidataIdentifier)"
            class="entity-icon-link"
          >
            <template #default>
              <img alt="Wikidata logo" src="@/assets/img/wikidata_logo.png" />
              Wikidata
            </template>
          </ExternalLinkAtom>
        </div>
      </div>
      <div v-if="bottomButtons.length > 0" class="entity-header__buttons">
        <div v-for="(button, index) of bottomButtons" :key="index">
          <ExternalLinkAtom
            v-if="button.link"
            class="special-button"
            :class="{ inverse: button.inverse }"
            :href="button.link"
          >
            <template #default>
              {{ button.label }}
              <font-awesome-icon
                v-if="button.icon"
                :icon="button.icon"
                class="fa-icon"
              />
            </template>
          </ExternalLinkAtom>
          <div v-else class="special-button">
            {{ button.label }}
            <font-awesome-icon
              v-if="button.icon"
              :icon="button.icon"
              class="fa-icon"
            />
          </div>
        </div>
      </div>
    </section>

    <section class="data-info">
      <InfrastructureInfoBox
        v-if="props.entity.infrastructure"
        :data="props.entity"
        :full-width="false"
        :breakdown-disclaimer="breakdownDisclaimer()"
      />
      <EmitterInfoBox v-else />
    </section>
  </div>
</template>

<style scoped>
.entity-meta > * {
  margin-bottom: min(2em, 4vh);
}

.entity-meta.desktop {
  --links-max-width: 200px;

  & .entity-header__grid {
    --first-col: v-bind("logoWidth");
    grid-template-columns: calc(var(--first-col) + 50px) 1fr;
    justify-items: initial;
    gap: 2em;

    & > div:first-child {
      margin: auto;
    }
  }

  & .entity-header__logo {
    grid-column: 1;
  }

  & .entity-header__desc {
    grid-column: 2;
  }

  & .entity-header__links {
    grid-column: 3;
    grid-row: 1;
    flex-direction: column;
    width: fit-content;
    max-width: var(--links-max-width);
  }

  & .entity-icon-link {
    width: 100%;
    padding: 0.75rem 1.25rem;

    & .icon,
    & img {
      margin-right: 0.2rem;
    }
  }

  & .entity-header__grid.three-columns {
    grid-template-columns: calc(var(--first-col) + 50px) 1fr var(
        --links-max-width
      );
  }
}

.entity-header__logo {
  text-align: center;
}

.data-info {
  position: relative;
  margin-left: auto;
  margin-right: auto;

  /*
  width: fit-content;

  & > * {
    width: min(90vw, 400px);
  }
  */
}

.entity-header__grid {
  display: grid;
  grid-template-columns: 100%;
  justify-items: center;
  align-items: center;
  gap: 1em;
  column-gap: 3em;
  margin: 1em 0;
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
    background-color: rgba(
      255,
      255,
      255,
      0.8
    ); /* Black with 50% transparency */
    z-index: -1; /* Ensure overlay is on top of the image */
  }
}

.entity-title {
  font-size: 3rem;
  line-height: 1.25;
}

.wiki-disclaimer {
  font-size: 0.9em;
  color: var(--p-gray-600);

  a {
    color: inherit;
  }
}

.entity-header__links {
  display: flex;
  flex-direction: row;
  width: 100%;
  column-gap: 1.5rem;
  row-gap: 0.25rem;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  margin: auto;
  padding: 1rem 0;
  border-radius: 15px;
  box-shadow:
    rgba(0, 0, 0, 0.1) 0px 1px 3px 0px,
    rgba(0, 0, 0, 0.1) 0px 1px 2px -1px;
}

.entity-icon-link {
  display: flex;
  flex-direction: row;
  gap: 0.65rem;
  align-items: center;
  text-decoration: unset;
  text-transform: uppercase;
  font-size: 0.9rem;

  padding: 0.2rem 0.25rem;
  &:hover {
    background-color: var(--p-surface-100);
    text-decoration: underline;
  }

  & img {
    width: 3rem;
  }

  & .fa-icon {
    width: 3rem;
    font-size: 2.25rem;
    color: var(--p-primary-700);
  }
}

.entity-header__buttons {
  padding: 0.7rem 0;
  display: flex;
  gap: min(3rem, 5vw);
  justify-content: center;
  flex-wrap: wrap;
}

.special-button {
  --color-1: var(--p-primary-600);
  --color-2: var(--p-primary-700);
  --color-invert: white;
  display: inline-block;
  column-gap: 1em;
  align-items: baseline;
  padding: 0.6rem 1.25rem;
  border: 2px solid var(--color-1);
  background-color: var(--color-1);
  color: var(--color-invert);
  border-radius: 4px;
  text-decoration: unset;
  transition: all 0.2s ease-out;

  & > .fa-icon {
    margin-left: 0.75rem;
  }

  &.inverse {
    background-color: var(--color-invert);
    color: var(--color-2);
    font-weight: 700;
  }
}

a.special-button:hover,
a.special-button:focus-visible {
  background-color: var(--color-invert);
  color: var(--color-2);

  &.inverse {
    background-color: var(--color-1);
    color: var(--color-invert);
  }
}
</style>
