<script setup lang="ts">
import Carousel from "primevue/carousel"
import { computed, onBeforeMount, onMounted, onUnmounted } from "vue"

import cosoLogoUrl from "@/assets/img/coso-black-logo.svg"
import gricadLogoUrl from "@/assets/img/logo_gricad_noir.svg"
import ugaLogoUrl from "@/assets/img/logo_UGA_noir_cmjn.jpg"
import mesrLogoUrl from "@/assets/img/mesr_logo_noir.png"
import ExternalLink from "@/components/atoms/ExternalLinkAtom.vue"
import ImageAtom from "@/components/atoms/ImageAtom.vue"
import CardComponent from "@/components/CardComponent.vue"
import EntityMap from "@/components/EntityMap.vue"
import { isDesktop, useMediaQuery } from "@/composables/useMediaQuery"
import { setBigHeader, togglePageNoHeader } from "@/singletons/fixedHeaderStore"
import { getEmitters, getPartners, type Entity } from "@/singletons/ref-data"
import { shuffleArray } from "@/utils/data-utils"
import {
  changeMetaDescripion,
  changeMetaTitle,
  changeMetaUrl,
} from "@/utils/dom-utils"
import { getEntityUrl } from "@/utils/url-utils"

changeMetaUrl(true)
changeMetaDescripion(
  "A data-driven platform to broaden funding for open science infrastructure..",
)
changeMetaTitle("Transparency to Sustain Open Science Infrastructure")

const partners = getPartners() as Entity[]
shuffleArray(partners)

const emitters = getEmitters() as Entity[]
const countries: string[] = []

emitters.forEach((e) => {
  if (e.country && !countries.includes(e.country)) {
    countries.push(e.country)
  }
})

const breakPoint1 = useMediaQuery("(min-width: 850px)", false)
const breakPoint2 = useMediaQuery("(min-width: 550px)", false)
const partnerLogoWidth = computed(() => {
  if (breakPoint1.value) {
    return "175px"
  } else if (breakPoint2.value) {
    return "150px"
  }
  return "100px"
})

onBeforeMount(() => {
  setBigHeader(true)
  togglePageNoHeader(true)
})

onMounted(() => {
  window.addEventListener("scroll", updateHeaderHome)
})

onUnmounted(() => {
  setBigHeader(false)
  togglePageNoHeader(false)
  window.removeEventListener("scroll", updateHeaderHome)
})

function updateHeaderHome() {
  setBigHeader(window.scrollY < 70)
}

const citations = [
  "TSOSI spotlights all the organizations that have supported open science infrastructure",
  "The more we highlight those who have funded, the more funders we will attract",
  "TSOSI aims to make funding to open science infrastructure the norm",
]
</script>

<template>
  <div id="home" :class="{ mobile: !isDesktop }">
    <section class="banner">
      <div class="container">
        <div class="content-section">
          <Carousel
            :value="citations"
            :num-visible="1"
            :num-scroll="1"
            circular
            :autoplay-interval="5000"
          >
            <template #item="slotProps">
              <div class="citation">
                <h2>
                  <span>
                    {{ slotProps.data }}
                  </span>
                </h2>
              </div>
            </template>
          </Carousel>
        </div>
      </div>
    </section>

    <section class="banner banner-dark">
      <div class="container">
        <div class="regular-content content-section">
          <h2 class="banner-title data-summary">
            So far, TSOSI includes
            <span class="number-emphasis">
              {{ emitters.length }}
            </span>
            organizations from
            <span class="number-emphasis">
              {{ countries.length.toString() }}
            </span>
            countries that have supported open science infrastructure.
          </h2>

          <EntityMap
            class="home-map"
            :id="'home-supporters-map'"
            :supporters="emitters"
            :data-loaded="true"
            :export-title-base="'overall supporters'"
          />
        </div>
      </div>
    </section>

    <section id="partner-banner" class="banner">
      <div class="container">
        <div class="regular-content content-section">
          <h2 class="banner-title" style="text-align: center">
            TSOSI data comes from the following organizations:
          </h2>
          <div class="partner-cards">
            <RouterLink
              :to="getEntityUrl(entity)"
              v-for="entity of partners"
              :key="entity.id"
              class="card-link"
            >
              <CardComponent :no-body="true">
                <template #header>
                  <ImageAtom
                    :src="entity.logo"
                    :width="partnerLogoWidth"
                    :center="true"
                  />
                </template>
              </CardComponent>
            </RouterLink>
          </div>
        </div>
        <div class="regular-content content-section">
          <h2 class="banner-title" style="text-align: center">
            Be part of this! See how to
            <RouterLink :to="'/pages/faq#join-tsosi'"> join TSOSI</RouterLink>.
          </h2>
          <!-- <div style="max-width: 700px; margin: 0 auto">
            <p :style="`margin-top: ${isDesktop ? '4em' : '2em'}`"></p>
          </div> -->
        </div>
      </div>
    </section>

    <section id="explain-banner" class="banner banner-dark">
      <div class="container">
        <div class="regular-content content-section">
          <h2 class="banner-title" style="text-align: center">
            How does it work?
          </h2>
          <div class="explain-boxes">
            <div class="explain-box" style="--l-pos: 80px">
              <h3>1. We collect financial data from TSOSI partners</h3>
              <p>
                We collect financial data from various organization. We started
                with infrastructures and we have added institutions.
              </p>
            </div>
            <div class="explain-box" style="--l-pos: calc(100% - 80px)">
              <h3>2. We enrich data with ROR and Wikidata identifiers</h3>
              <p>
                Which allows to deduplicate and retrieve descriptions and logos
                from Wikipedia
              </p>
            </div>
            <div class="explain-box">
              <h3>3. We ingest data in TSOSI software</h3>
              <p>
                So that everyone can explore this data, and wants to contribute
                to open infrastructure
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
    <section id="who-is-behind" class="banner">
      <div class="container">
        <div class="regular-content content-section">
          <h2 class="banner-title" style="text-align: center">
            Who is behind TSOSI?
          </h2>
          <div class="partner-cards">
            <ExternalLink
              href="https://www.enseignementsup-recherche.gouv.fr/fr"
              class="card-link"
            >
              <CardComponent :no-body="true">
                <template #header>
                  <ImageAtom
                    :src="mesrLogoUrl"
                    :width="'120px'"
                    :height="'110px'"
                    :center="true"
                  />
                </template>
              </CardComponent>
            </ExternalLink>
            <ExternalLink
              href="https://www.ouvrirlascience.fr/home/"
              class="card-link"
            >
              <CardComponent :no-body="true">
                <template #header>
                  <ImageAtom
                    :src="cosoLogoUrl"
                    :width="'150px'"
                    :height="'100px'"
                    :center="true"
                  />
                </template>
              </CardComponent>
            </ExternalLink>
            <ExternalLink
              href="https://www.univ-grenoble-alpes.fr/english/"
              class="card-link"
            >
              <CardComponent :no-body="true">
                <template #header>
                  <ImageAtom
                    :src="ugaLogoUrl"
                    :width="'100px'"
                    :height="'100px'"
                    :center="true"
                  />
                </template>
              </CardComponent>
            </ExternalLink>
            <ExternalLink
              href="https://gricad.univ-grenoble-alpes.fr/en/"
              class="card-link"
            >
              <CardComponent :no-body="true">
                <template #header>
                  <ImageAtom
                    :src="gricadLogoUrl"
                    :width="'90px'"
                    :height="'100px'"
                    :center="true"
                  />
                </template>
              </CardComponent>
            </ExternalLink>
          </div>
          <div style="text-align: center">
            <RouterLink :to="'/pages/about'">
              See governance and partners
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
#home > *:first-child {
  padding-top: 15vh;
}

#home.mobile {
  .citation,
  .citation h2 {
    font-size: 2.8rem;
  }

  .banner-title {
    font-size: 1.75rem;
  }

  .grid-2-cols {
    grid-template-columns: 1fr;
  }
}

.citation {
  height: 100%;
  margin: auto auto;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.citation h2 {
  max-width: 1000px;
  font-size: 5rem;
  font-weight: 400;
  line-height: 1.4;
}

.logo {
  max-width: 100%;
}

.data-summary {
  padding: min(1rem, 3vw);
  border-radius: 20px;
  font-weight: 700;
}

.banner {
  width: 100%;
  padding: 4vh 0;

  &.banner-dark {
    background-color: var(--p-gray-100);
  }
}

.banner-title {
  font-size: 2.5rem;
  text-align: left;
}

.partner-cards {
  margin: 2rem auto;
  display: flex;
  flex-wrap: wrap;
  row-gap: 1em;
  column-gap: 2em;
  justify-content: space-around;
  max-width: 800px;
}

.card-link {
  display: block;
  text-decoration: unset;

  &:deep(.card) {
    padding: 10px;
    box-shadow: unset;
  }

  &:hover,
  &:focus-visible {
    text-decoration: underline;
    outline: unset;

    & :deep(.card) {
      box-shadow:
        rgba(0, 0, 0, 0.1) 0px 1px 5px 5px,
        rgba(0, 0, 0, 0.1) 0px 1px 2px -1px;
    }
  }

  &:focus-visible {
    & :deep(.card) {
      outline: 2px solid var(--p-primary-color);
    }
  }
}

.content-section {
  display: flex;
  flex-direction: column;
  row-gap: 4vh;
}

.number-emphasis {
  font-weight: 700;
  font-size: 1.15em;
  color: var(--p-primary-color);
  padding: 5px;
  border-radius: 5px;
  box-shadow: 0 0 6px 1px var(--p-surface-300);
}

.home-map :deep(.map-container) {
  height: min(40rem, 75vh);
}

.explain-box {
  --b-margin: 5rem;
  --box-color: var(--b-col, var(--p-surface-300));
  position: relative;
  padding: 2em;
  border-radius: 20px;
  max-width: 650px;
  margin: 0 auto var(--b-margin);
  border: 2px solid var(--box-color);

  & h3 {
    font-size: 1.5rem;
  }

  &::after {
    content: "";
    position: absolute;
    top: calc(100% + 1px);
    left: var(--l-pos, calc(50% - 1px));
    height: calc(var(--b-margin) + 2px);
    width: 2px;
    background-color: var(--box-color);
  }

  &::before {
    --arrow-size: 14px;
    content: "";
    position: absolute;
    top: calc(100% + 1px + var(--b-margin) - var(--arrow-size));
    left: calc(var(--l-pos, calc(50%)) + 1px - (var(--arrow-size) / 2));
    transform: rotate(45deg);
    width: var(--arrow-size);
    height: var(--arrow-size);
    border-bottom: 4px solid var(--box-color);
    border-right: 4px solid var(--box-color);
    border-radius: 4px;
    animation: arrow-anim 1s linear infinite;
  }

  &:last-child {
    margin-bottom: 0;

    &::after {
      all: unset;
    }

    &::before {
      all: unset;
    }
  }
}

@keyframes arrow-anim {
  0% {
    opacity: 0.2;
    transform: translateY(-5rem) rotate(45deg);
  }

  50% {
    opacity: 1;
    transform: translateY(-2.5rem) rotate(45deg);
  }

  100% {
    opacity: 0.2;
    transform: rotate(45deg);
  }
}

.grid-2-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2em;
  row-gap: 4em;
}
</style>
