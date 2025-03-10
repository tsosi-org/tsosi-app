<script setup lang="ts">
import {
  getEmitters,
  getInfrastructures,
  type Entity,
} from "@/singletons/ref-data"
import { changeTitle } from "@/utils/dom-utils"
import EntityMap from "@/components/EntityMap.vue"
import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"
import InfrastructurePopup from "@/components/InfrastructurePopup.vue"
import InfrastructureCard from "@/components/InfrastructureCard.vue"
import { shuffleArray } from "@/utils/data-utils"

changeTitle("Home")

const infrastructures = getInfrastructures() as Entity[]
shuffleArray(infrastructures)
const emitters = getEmitters() as Entity[]
const countries: string[] = []

emitters.forEach((e) => {
  if (e.country && !countries.includes(e.country)) {
    countries.push(e.country)
  }
})
</script>

<template>
  <div>
    <div class="container">
      <div class="regular-content">
        <div class="data-summary">
          <span class="number-emphasis">
            {{ emitters.length }}
          </span>
          institutions from
          <span class="number-emphasis">
            {{ countries.length.toString() }}
          </span>
          countries contributed to sustain
          <InfoButtonAtom
            :label="infrastructures.length.toString()"
            class="number-emphasis"
          >
            <template #default>
              <InfrastructurePopup />
            </template>
          </InfoButtonAtom>
          Open Science Infrastructures.
        </div>
        <EntityMap
          class="home-map"
          :infrastructures="infrastructures"
          :supporters="emitters"
          title="Funder locations"
          :data-loaded="true"
        />
      </div>
    </div>
    <div class="banner-dark">
      <div class="container">
        <div class="regular-content">
          <h1>Partners</h1>
          <div
            class="partner-cards"
            style="
              margin: 2rem 0;
              display: flex;
              gap: 2em;
              justify-content: space-around;
              flex-wrap: wrap;
            "
          >
            <InfrastructureCard
              v-for="entity of infrastructures"
              :entity="entity"
              :key="entity.id"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-summary {
  font-size: 2rem;
  padding: 1rem;
  /* box-shadow: 0 0 6px 1px var(--p-surface-300); */
  border-radius: 20px;
  margin-bottom: 2rem;
}

.banner-dark {
  background-color: var(--p-surface-300);
  width: 100%;
  padding: 4vh 0;
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
