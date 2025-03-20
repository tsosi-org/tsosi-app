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

const props = defineProps<{
  entity: EntityDetails
}>()

const logoWidth = computed(() => (isDesktop.value ? "200px" : "125px"))
const logoHeight = computed(() => (isDesktop.value ? "150px" : "125px"))
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
    const backerName = props.entity.infrastructure?.backer_name
    if (backerName) {
      countryChip.info = `
        ${props.entity.name} is maintained by ${backerName},
        located in ${countryName}
      `
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
        icon: "arrow-up-right-from-square",
        label: "Committed to POSI",
        link: props.entity.infrastructure.posi_url,
      })
    }
    if (props.entity.infrastructure.infra_finder_url) {
      bottomButtons.value.push({
        icon: "arrow-up-right-from-square",
        label: "Included in InfraFinder",
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
        icon: "square-check",
        label: `SCOSS selected for ${dateStart}-${dateEnd}`,
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
    <section>
      <div
        class="entity-header"
        :class="{ 'three-columns': hasLinks && !isInfrastructure }"
      >
        <div v-if="isDesktop || props.entity?.logo" class="entity-header__logo">
          <Image
            :src="props.entity?.logo"
            :width="logoWidth"
            :height="logoHeight"
            :center="true"
          />
          <a
            v-if="isInfrastructure && props.entity.website"
            :href="props.entity.website"
            rel="noopener noreferrer"
            target="_blank"
            >{{ props.entity.website.split("://").at(-1) }}</a
          >
        </div>
        <div class="entity-header__title">
          <h1 class="entity-title">
            <span>{{ props.entity.name }}</span>
          </h1>
          <ChipList :chips="headerChips" :center="!isDesktop" />
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
                <a
                  :href="props.entity.wikipedia_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  >Wikipedia</a
                >
                licensed
                <a
                  href="https://en.wikipedia.org/wiki/Wikipedia:Text_of_the_Creative_Commons_Attribution-ShareAlike_4.0_International_License"
                  target="_blank"
                  rel="noopener noreferrer"
                  >CC-BY-SA</a
                >
              </span>
            </p>
          </div>
          <div v-else>
            Open Access list of financial support made or received by
            {{ props.entity.name }} from 2XXX to 2XXX.
          </div>
        </div>
        <div
          v-if="props.entity.infrastructure == null && hasLinks"
          class="entity-header__links"
        >
          <a
            v-if="props.entity.website"
            class="entity-icon-link"
            :href="props.entity.website"
            target="_blank"
            rel="noopener noreferrer"
          >
            <font-awesome-icon class="fa-icon" icon="globe" />
            Website
          </a>
          <a
            v-if="rorIdentifier"
            class="entity-icon-link"
            :href="getRorUrl(rorIdentifier)"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img alt="ROR logo" src="@/assets/img/ror_icon_rgb.svg" />
            Record
          </a>
          <a
            v-if="wikidataIdentifier"
            class="entity-icon-link"
            :href="getWikidataUrl(wikidataIdentifier)"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img alt="Wikidata logo" src="@/assets/img/wikidata_logo.png" />
            Item
          </a>
        </div>
      </div>

      <div class="buttons">
        <div v-for="(button, index) of bottomButtons" :key="index">
          <a
            v-if="button.link"
            class="special-button"
            :href="button.link"
            target="_blank"
            rel="noopener noreferre"
          >
            {{ button.label }}
            <font-awesome-icon
              v-if="button.icon"
              :icon="button.icon"
              class="fa-icon"
            />
          </a>
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

    <section
      v-if="props.entity.infrastructure?.support_url"
      class="support-banner"
    >
      <a
        class="support-link"
        :href="props.entity.infrastructure.support_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <span>SUPPORT</span>
        <br />
        <h3>{{ props.entity.name }}</h3>
      </a>
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
  & .entity-header {
    --first-col: v-bind("logoWidth");
    grid-template-columns: calc(var(--first-col) + 50px) 1fr;
    justify-items: initial;

    & > div:first-child {
      margin: auto;
      padding-top: 0.5em;
    }
  }

  & .entity-header__logo {
    grid-column: 1;
    grid-row: 1 / span 2;
  }

  & .entity-header__title {
    text-align: initial;
    grid-row: 1;
  }

  & .entity-header__desc {
    grid-row: 2;
  }

  & .entity-header__links {
    grid-column: 3;
    grid-row: 1 / span 2;
    flex-direction: column;
  }

  & .entity-icon-link {
    width: 100%;
    padding: 0.75rem 1.25rem;

    & .icon,
    & img {
      margin-right: 0.2rem;
    }
  }

  & .entity-header.three-columns {
    grid-template-columns: calc(var(--first-col) + 50px) 1fr 150px;
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

.entity-header {
  display: grid;
  grid-template-columns: 100%;
  justify-items: center;
  gap: 1em;
  padding: min(1em, 1vw);
  column-gap: 3em;
}

.entity-header__title {
  position: relative;
  text-align: center;
  flex-direction: column;
  gap: 1em;
  grid-row: 1;
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

.support-banner {
  text-align: center;
}

.support-link {
  display: inline-block;
  min-width: 250px;
  font-size: 1.25rem;
  padding: 1rem 2rem;
  outline: 3px solid transparent;
  border-radius: 50px;
  font-weight: bold;
  line-height: 1.7;
  /* background: linear-gradient(
    to right bottom,
    var(--p-primary-400),
    30%,
    var(--p-primary-700)
  );
  color: white; */
  background: linear-gradient(
    to right bottom,
    var(--p-amber-100),
    25%,
    var(--p-amber-200)
  );
  color: var(--p-amber-800);
  text-decoration: unset;
  transition: 0.3s outline-color ease-in;
  animation: 1.5s shake linear 1.5s 1;
  box-shadow: rgb(0, 0, 0, 0.15) 2px 5px 3px 1px;

  &:hover,
  &:focus-visible {
    outline-color: var(--p-amber-200);
    background: var(--p-amber-200);
  }

  & h3 {
    color: inherit;
    padding: 0.2rem 1rem;
  }
}

@keyframes shake {
  50%,
  95% {
    transform: translate3d(-1px, 0, 0);
  }

  55%,
  90% {
    transform: translate3d(2px, 0, 0);
  }

  60%,
  70%,
  80% {
    transform: translate3d(-4px, 0, 0);
  }

  65%,
  75% {
    transform: translate3d(4px, 0, 0);
  }
}

.buttons {
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
}

a.special-button:hover,
a.special-button:focus-visible {
  background-color: var(--color-invert);
  color: var(--color-2);
}
</style>
