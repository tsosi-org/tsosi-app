<script setup lang="ts">
import ugaLogoUrl from "@/assets/img/logo_UGA_noir_cmjn.jpg"
import cosoLogoUrl from "@/assets/img/coso-black-logo.svg"
import { getEmitters, getPartners, type Entity } from "@/singletons/ref-data"
import {
  changeMetaTitle,
  changeMetaDescripion,
  changeMetaUrl,
} from "@/utils/dom-utils"
import EntityMap from "@/components/EntityMap.vue"
import CardComponent from "@/components/CardComponent.vue"
import { shuffleArray } from "@/utils/data-utils"
import ImageAtom from "@/components/atoms/ImageAtom.vue"
import { getEntityUrl } from "@/utils/url-utils"
import { isDesktop, useMediaQuery } from "@/composables/useMediaQuery"
import { onBeforeMount, onMounted, onUnmounted, computed } from "vue"
import { togglePageNoHeader, setBigHeader } from "@/singletons/fixedHeaderStore"
import Carousel from "primevue/carousel"
import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"

changeMetaUrl(true)
changeMetaDescripion(
  "Web platform visualizing the funding made to Open Science Infrastructures.",
)
changeMetaTitle("TSOSI - Transparency to Sustain Open Science Infrastructure")

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
    console.log("Breakpoint 1")
    return "175px"
  } else if (breakPoint2.value) {
    console.log("Breakpoint 2")
    return "150px"
  }
  console.log("No breakpoint")
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
          <div class="banner-title data-summary">
            So far, TSOSI includes
            <span class="number-emphasis">
              {{ emitters.length }}
            </span>
            organizations from
            <span class="number-emphasis">
              {{ countries.length.toString() }}
            </span>
            countries that have financially contributed to
            <RouterLink to="#partner-banner">
              partner's infrastructure
            </RouterLink>
          </div>

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
            For its launching, TSOSI includes data from the partners
            infrastructure
          </h2>

          <!-- TO BE REMOVED once carousel is validated -->
          <div class="partner-cards">
            <RouterLink
              :to="getEntityUrl(entity.id)"
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
                For its launching, the data comes from partners infrastructure
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

    <section id="join-banner" class="banner">
      <div class="container">
        <div class="regular-content content-section">
          <div class="grid-2-cols">
            <div>
              <h2 class="banner-title" style="text-align: center">
                How to join TSOSI?
              </h2>
              <div style="max-width: 700px; margin: 0 auto">
                <p :style="`margin-top: ${isDesktop ? '4em' : '2em'}`">
                  The project started in September 2024, and the platform was
                  launched in June 2025. Any support and feedback are really
                  welcome. If you represent an institution, a consortium or an
                  infrastructure, feel free to drop us a line
                  <CodeBlockAtom
                    :content="'contact (@tsosi.org)'"
                    :inline="true"
                    :background="true"
                  />
                </p>
              </div>
            </div>
            <div>
              <h2 class="banner-title" style="text-align: center">
                Who is behind TSOSI?
              </h2>
              <div
                style="
                  max-width: 700px;
                  margin: 0 auto;
                  display: flex;
                  flex-wrap: wrap;
                  justify-content: space-around;
                  align-items: center;
                "
              >
                <ImageAtom
                  :src="ugaLogoUrl"
                  :width="isDesktop ? '150px' : '125px'"
                  :center="true"
                />
                <ImageAtom
                  :src="cosoLogoUrl"
                  :width="isDesktop ? '200px' : '150px'"
                  :center="true"
                />
              </div>
              <div style="text-align: center">
                <RouterLink :to="'/pages/about'">
                  See governance and partners
                </RouterLink>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
#home > *:first-child {
  padding-top: 3vh;
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
    top: calc(100% + 2px);
    left: var(--l-pos, calc(50% - 1px));
    height: var(--b-margin);
    width: 2px;
    background-color: var(--box-color);
  }

  &:last-child {
    margin-bottom: 0;

    &::after {
      all: unset;
    }
  }
}

.grid-2-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2em;
  row-gap: 4em;
}
</style>
