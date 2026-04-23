<script setup lang="ts">
import { type Entity } from "@/singletons/ref-data"
import { getEntityUrl } from "@/utils/url-utils"
import { ref, type Ref } from "vue"
import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"
import ProviderCorner from "./atoms/ProviderCornerAtom.vue"

interface EntityCardProps {
  entity: Entity
  amounts?: Record<string, number>
  currency?: string
}

const props = defineProps<EntityCardProps>()
const entity: Ref<Entity | null> = ref(props.entity)
</script>

<template>
  <RouterLink
    v-if="entity"
    :to="getEntityUrl(entity)"
    class="container"
  >
    <ProviderCorner v-if="entity.is_partner" />
    <div class="info-container">
      <div class="top-container">
        <div class="logo-container">
          <img
            v-if="entity.logo"
            class="logo"
            :src="entity.logo"
          />
          <h2 class="name" v-else>
            {{ entity.short_name || entity.name.slice(0, 60) }}
          </h2>
        </div>
        <!-- <div class="types-container">
          <Chip
            v-if="entity.country"
            :label="getCountryLabel(entity.country)"
          >
            <template #icon>
              <font-awesome-icon :icon="['fas', 'location-dot']" />
            </template>
          </Chip>
          <Chip
            v-if="entity.date_inception"
            :label="`Since ${entity.date_inception.getFullYear()}`"
          >
            <template #icon>
              <font-awesome-icon :icon="['fas', 'calendar']" />
            </template>
          </Chip>
        </div> -->
        <!-- <div class="name-container">
      </div> -->
        <!-- <div
        class="desc-container"
        v-if="entity.description || entity.wikipedia_extract"
      >
        <p class="desc">
          {{ entity.description || entity.wikipedia_extract }}
        </p>
      </div> -->
      </div>
      <div v-if="props.amounts" class="meta-container">
        <div class="meta-entry" v-if="entity.infrastructure?.posi_url">
          <ExternalLinkAtom
            :href="entity.infrastructure.posi_url"
            aria-label="Link to POSI declaration"
          >
            <p>POSI adopter</p>
            <font-awesome-icon class="fa-icon" :icon="['fas', 'link']" />
          </ExternalLinkAtom>
        </div>
        <div
          class="meta-entry"
          v-if="
            entity.infrastructure?.date_scoss_start &&
            entity.infrastructure?.posi_url
          "
        >
          <ExternalLinkAtom
            :href="entity.infrastructure.posi_url"
            aria-label="Link to Infrafinder page"
          >
            <p>SCOSS selected</p>
            <font-awesome-icon
              class="fa-icon"
              :icon="['fas', 'circle-question']"
            />
          </ExternalLinkAtom>
        </div>
      </div>
    </div>
    <!-- <div class="see-more">Show data</div> -->
    <div v-if="props.amounts" class="amount-container">
      <p class="amount">
        {{ props.amounts[props.currency || "EUR"]?.toLocaleString() || "0" }}
        {{ props.currency || "EUR" }}
      </p>
      <p class="subamount">since 2012</p>
    </div>
  </RouterLink>
</template>

<style scoped>
.container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: start;
  width: 250px;
  height: 250px;
  padding: 0;
  margin: 0;
  border-radius: 15px;
  box-shadow:
    rgba(0, 0, 0, 0.2) 0px 1px 3px 0px,
    rgba(0, 0, 0, 0.2) 0px 1px 2px -1px;
  text-decoration: none;
  overflow: hidden;
}

a.container:hover {
  box-shadow:
    rgba(0, 0, 0, 0.3) 0px 4px 6px -1px,
    rgba(0, 0, 0, 0.22) 0px 2px 4px -1px;
}

.info-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  padding: 10px;
}

.top-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.logo-container {
  width: 100%;
  height: 100px;
  margin-top: 10px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  width: 70%;
  height: 100%;
  object-fit: contain;
}

.name {
  text-align: center;
  font-size: 1.2em;
}

.types-container {
  margin-top: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.p-chip {
  line-height: 1;
  font-size: 12px;
  margin: 5px;
}

.country-container {
  height: 15px;
  line-height: 1;
}

.desc {
  text-align: justify;
  font-size: 0.9em;
  margin: 0;
}

.meta-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: start;
}

.meta-entry {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  border-radius: 5px;
  margin-bottom: 10px;

  a {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    height: 100%;
    padding: 0px 10px;
    text-decoration: none;
    border-radius: 5px;
    background-color: var(--p-neutral-200);
  }
  a:hover {
    background-color: var(--p-neutral-300);
  }
}

.amount-container {
  height: 80px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: var(--p-primary-100);
  border-top: 1px solid var(--p-primary-200);
  border-radius: 0px 0px 15px 15px;

  p {
    padding: 0;
    margin: 0;
    color: black;
  }
}

.amount {
  font-weight: 700;
  font-size: 1.2em;
}

.see-more {
  font-size: 0.9em;
  color: var(--p-primary-700);
  font-weight: 500;
  margin-bottom: 10px;
}
</style>
