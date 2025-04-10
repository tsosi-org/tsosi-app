<script setup lang="ts">
import {
  getEmitters,
  getInfrastructures,
  getPartners,
  type Entity,
} from "@/singletons/ref-data"
import {
  changeMetaTitle,
  changeMetaDescripion,
  changeMetaUrl,
} from "@/utils/dom-utils"
import EntityMap from "@/components/EntityMap.vue"
import CardComponent from "@/components/CardComponent.vue"
import { shuffleArray } from "@/utils/data-utils"
import ImageAtom from "@/components/atoms/ImageAtom.vue"
import SearchBar from "@/components/SearchBar.vue"
import { getEntityUrl } from "@/utils/url-utils"
import { isDesktop } from "@/composables/useMediaQuery"
import { onBeforeMount, onMounted, onUnmounted } from "vue"
import { togglePageNoHeader, setBigHeader } from "@/singletons/fixedHeaderStore"
import Carousel from "primevue/carousel"

changeMetaUrl(true)
changeMetaDescripion(
  "Web platform visualizing the funding made to Open Science Infrastructures.",
)
changeMetaTitle("TSOSI - Transparency to Sustain Open Science Infrastructure")

const infrastructures = getInfrastructures() as Entity[]
const partners = getPartners() as Entity[]
shuffleArray(partners)

const emitters = getEmitters() as Entity[]
const countries: string[] = []

emitters.forEach((e) => {
  if (e.country && !countries.includes(e.country)) {
    countries.push(e.country)
  }
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
</script>

<template>
  <div id="home" :class="{ 'home-mobile': !isDesktop }">
    <section class="banner">
      <div class="container">
        <div class="regular-content content-section citation">
          <div>
            <h2>
              No reason to hide a contribution made to an Open Science
              Infrastructure.
            </h2>
          </div>
          <div class="hr"></div>
          <div class="subtitle">
            TSOSI was born of the idea that all funding, subsidies and support
            should be transparent, so that we can better understand the issues
            behind the OS infrastructures.
            <br />
            <RouterLink to="/pages/about"> Read more. </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <section class="banner banner-dark">
      <div class="container">
        <div class="regular-content content-section">
          <div class="data-summary">
            So far, TSOSI includes
            <span class="number-emphasis">
              {{ emitters.length }}
            </span>
            organizations from
            <span class="number-emphasis">
              {{ countries.length.toString() }}
            </span>
            countries that contributed to sustain
            <RouterLink to="#partner-banner" class="number-emphasis">
              {{ infrastructures.length.toString() }}
            </RouterLink>
            Open Science Infrastructures.
          </div>
        </div>
      </div>
    </section>
    <section class="banner">
      <div class="container">
        <div class="regular-content content-section">
          <EntityMap
            class="home-map"
            :id="'home-supporters-map'"
            :supporters="emitters"
            :title="'Location of the supporters'"
            :data-loaded="true"
          />
        </div>
      </div>
    </section>

    <section id="partner-banner" class="banner banner-dark">
      <div class="container">
        <div class="regular-content content-section">
          <h1 style="text-align: center">Our Partners</h1>
          <Carousel
            :value="partners"
            :numVisible="4"
            :numScroll="1"
            circular
            :responsive-options="[
              {
                breakpoint: '1150px',
                numVisible: 3,
                numScroll: 1,
              },
              {
                breakpoint: '850px',
                numVisible: 2,
                numScroll: 1,
              },
              {
                breakpoint: '600px',
                numVisible: 1,
                numScroll: 1,
              },
            ]"
          >
            <template #item="slotProps">
              <RouterLink
                :to="getEntityUrl(slotProps.data.id)"
                class="card-link"
              >
                <CardComponent>
                  <template #header>
                    <ImageAtom
                      :src="slotProps.data.logo"
                      :width="'150px'"
                      :center="true"
                    />
                  </template>
                  <template #title>
                    {{ slotProps.data.name }}
                  </template>
                </CardComponent>
              </RouterLink>
            </template>
          </Carousel>

          <!-- TO BE REMOVED once carousel is validated -->
          <div class="partner-cards" style="display: none">
            <CardComponent
              v-for="entity of partners"
              :entity="entity"
              :key="entity.id"
            >
              <template #header>
                <ImageAtom
                  :src="entity.logo"
                  width="max(min(17vw, 12rem), 150px)"
                  :center="true"
                />
              </template>
              <template #title>
                <RouterLink :to="getEntityUrl(entity.id)">
                  {{ entity.name }}
                </RouterLink>
              </template>
            </CardComponent>
          </div>

          <SearchBar
            width="min(80vw, 800px)"
            class="large"
            place-holder="Search for institutions"
          />
        </div>
      </div>
    </section>

    <section id="explain-banner" class="banner">
      <div class="container">
        <div class="regular-content content-section">
          <div
            class="explain-cards"
            style="
              display: flex;
              flex-direction: row;
              flex-wrap: wrap;
              gap: 1.5em;
              justify-content: space-around;
            "
          >
            <CardComponent width="24rem">
              <template #title>
                <h3 class="as-h1">Why ?</h3>
              </template>
              <template #content>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. In
                interdum, odio in aliquam ornare, nunc tellus euismod mi, vitae
                varius enim risus vel quam. Proin fringilla nec quam vel
                consectetur. Cras pharetra tempus dapibus. Sed libero turpis,
                dapibus et tortor id, vestibulum congue sapien. Phasellus erat
                mi, interdum eu euismod aliquam, ultricies nec nibh. Etiam nec
                malesuada elit. Nunc scelerisque metus eget turpis rhoncus
                egestas.
              </template>
            </CardComponent>
            <CardComponent width="24rem">
              <template #title>
                <h3 class="as-h1">How ?</h3>
              </template>
              <template #content>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. In
                interdum, odio in aliquam ornare, nunc tellus euismod mi, vitae
                varius enim risus vel quam. Proin fringilla nec quam vel
                consectetur. Cras pharetra tempus dapibus. Sed libero turpis,
                dapibus et tortor id, vestibulum congue sapien. Phasellus erat
                mi, interdum eu euismod aliquam, ultricies nec nibh. Etiam nec
                malesuada elit. Nunc scelerisque metus eget turpis rhoncus
                egestas.
              </template>
            </CardComponent>
            <CardComponent width="24rem">
              <template #title>
                <h3 class="as-h1">When ?</h3>
              </template>
              <template #content>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. In
                interdum, odio in aliquam ornare, nunc tellus euismod mi, vitae
                varius enim risus vel quam. Proin fringilla nec quam vel
                consectetur. Cras pharetra tempus dapibus. Sed libero turpis,
                dapibus et tortor id, vestibulum congue sapien. Phasellus erat
                mi, interdum eu euismod aliquam, ultricies nec nibh. Etiam nec
                malesuada elit. Nunc scelerisque metus eget turpis rhoncus
                egestas.
              </template>
            </CardComponent>
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

.home-mobile {
  .citation,
  .citation h2 {
    font-size: 2.8rem;

    & .subtitle {
      width: initial;
    }
  }

  .data-summary {
    font-size: 1.75rem;
  }
}

.citation {
  padding: 0 min(0.8em, 4vw);

  & .hr {
    content: "";
    height: 2px;
    width: 50%;
    /* margin-left: min(1em, 4vw); */
    background-color: var(--color-heading);
  }

  & .subtitle {
    font-size: 1rem;
    width: 50%;
  }
}

.citation,
.citation h2 {
  font-size: 5rem;
  font-weight: 400;
  line-height: 1.4;
}

.logo {
  max-width: 100%;
}

.home-mobile {
  & .partner-cards {
    grid-template-columns: 1fr;
    justify-items: center;
    & :deep(.card) {
      width: min(100%, 450px);
    }
  }
}

.data-summary {
  font-size: 2.25rem;
  padding: min(1rem, 3vw);
  border-radius: 20px;
  font-weight: 700;
}

.banner {
  width: 100%;
  padding: 4vh 0;
}

.banner-dark {
  background-color: var(--p-gray-100);
}

.partner-cards {
  margin: 2rem 0;
  display: grid;
  row-gap: 2em;
  column-gap: 1.25em;
  grid-template-columns: 1fr;
  grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
  justify-content: space-around;
}

.card-link {
  display: block;
  text-decoration: unset;
  margin: 8px 1.5em;
  /* height: calc(100% - 16px); */

  & :deep(.card) {
    min-height: 250px;
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

.explain-cards :deep(.card) {
  color: white;
  background: transparent
    linear-gradient(115deg, var(--p-primary-400), 30%, var(--p-primary-700));
  /* background-color: var(--p-primary-700); */

  & :deep(h3) {
    color: white;
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
  height: 40rem;
}
</style>
