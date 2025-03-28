<script setup lang="ts">
import { type EntityDetails } from "@/singletons/ref-data"
import Image from "./atoms/ImageAtom.vue"
import Chip from "primevue/chip"
import { getRorUrl } from "@/utils/url-utils"
import { isDesktop } from "@/composables/useMediaQuery"
import { getCountryLabel } from "@/utils/data-utils"
import InfrastructureInfoBox from "@/components/InfrastructureInfoBox.vue"
import EmitterInfoBox from "@/components/EmitterInfoBox.vue"

interface IconLabel {
  label: string
  icon?: string
  iconText?: string
  link?: string
}

const props = defineProps<{
  entity: EntityDetails
}>()

const logoWidth = "200px"

const iconLabels: Array<IconLabel> = []
if (props.entity.country) {
  iconLabels.push({
    icon: "location-dot",
    label: getCountryLabel(props.entity.country),
  })
}

if (props.entity.date_inception) {
  iconLabels.push({
    icon: "calendar",
    label: `Since ${props.entity.date_inception.getFullYear()}`,
  })
}

if (props.entity.website) {
  iconLabels.push({
    icon: "arrow-up-right-from-square",
    label: "Website",
    link: props.entity.website,
  })
}

props.entity.identifiers
  .filter((id) => id.registry == "ror")
  .map((id) =>
    iconLabels.push({
      icon: "arrow-up-right-from-square",
      iconText: "ROR ID:",
      label: id.value,
      link: getRorUrl(id.value),
    }),
  )

// Infrastructure specific chips
if (props.entity.infrastructure) {
  if (props.entity.infrastructure.infra_finder_url) {
    iconLabels.push({
      icon: "arrow-up-right-from-square",
      label: "InfraFinder",
      link: props.entity.infrastructure.infra_finder_url,
    })
  }
  if (props.entity.infrastructure.posi_url) {
    iconLabels.push({
      icon: "arrow-up-right-from-square",
      label: "POSI",
      link: props.entity.infrastructure.posi_url,
    })
  }
  if (props.entity.infrastructure.is_scoss_awarded) {
    iconLabels.push({
      icon: "square-check",
      label: "SCOSS awarded",
    })
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
    <div>
      <div v-if="isDesktop" class="entity-header-desktop">
        <div>
          <Image
            :src="props.entity?.logo"
            :width="logoWidth"
            :height="'150px'"
            :center="true"
          />
        </div>
        <div style="display: flex; flex-direction: column; gap: 1em">
          <h1 class="entity-title">
            <span>{{ props.entity.name }}</span>
          </h1>
          <div v-if="props.entity.wikipedia_extract">
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
          <div v-else-if="props.entity.description">
            <p>
              {{ props.entity.description }}
            </p>
          </div>
          <div v-else>
            Open Access list of financial support made or received by
            {{ props.entity.name }} from 2XXX to 2XXX.
          </div>
        </div>
      </div>

      <div v-else class="entity-header-mobile">
        <div
          style="
            display: flex;
            gap: 2em;
            margin-bottom: 1em;
            place-items: center;
          "
        >
          <Image
            :src="props.entity?.logo"
            :width="'60px'"
            :height="'50px'"
            :center="true"
          />
          <h1 class="entity-title">
            <span>{{ props.entity.name }}</span>
          </h1>
        </div>
        <div v-if="props.entity.wikipedia_extract" class="entity-description">
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

      <div class="icon-label-list">
        <div v-for="(iconLabel, index) of iconLabels" :key="index">
          <a
            v-if="iconLabel.link"
            :href="iconLabel.link"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Chip
              class="chip-link"
              :label="iconLabel.label"
              :dt="{ gap: '0.8em', padding: { y: '0.6em', x: '1em' } }"
              pt:root:class="chip-link"
              pt:label:class="chip-link-label"
            >
              <template #icon>
                <div class="chip-icon-group">
                  <font-awesome-icon
                    v-if="iconLabel.icon"
                    class="icon"
                    :icon="iconLabel.icon"
                  />
                  <span v-if="iconLabel.iconText">{{
                    iconLabel.iconText
                  }}</span>
                </div>
              </template>
            </Chip>
          </a>
          <Chip
            v-else
            :label="iconLabel.label"
            :dt="{ gap: '0.8em', padding: { y: '0.6em', x: '1em' } }"
          >
            <template #icon>
              <div class="chip-icon-group">
                <font-awesome-icon
                  v-if="iconLabel.icon"
                  class="icon"
                  :icon="iconLabel.icon"
                />
                <span v-if="iconLabel.iconText">{{ iconLabel.iconText }}</span>
              </div>
            </template>
          </Chip>
        </div>
      </div>
    </div>
    <InfrastructureInfoBox
      v-if="props.entity.infrastructure"
      :data="props.entity as EntityDetails"
      style="margin: 1em 0"
      :full-width="true"
      :breakdown-disclaimer="breakdownDisclaimer()"
    />
    <EmitterInfoBox v-else />
  </div>
</template>

<style scoped>
.entity-meta.desktop {
  display: grid;
  grid-template-columns: 1fr 350px;
  column-gap: 1em;
}

.entity-header {
  text-align: center;
}

.entity-header-desktop {
  --first-col: v-bind("logoWidth");
  display: grid;
  grid-template-columns: calc(var(--first-col) + 50px) 1fr;
  gap: 1em;
  padding: 1em;

  & > div:first-child {
    margin: auto;
    padding-top: 0.5em;
  }
}

.wiki-disclaimer {
  font-size: 0.9em;
  color: var(--p-gray-600);

  a {
    color: inherit;
  }
}

.icon-label-list {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  row-gap: 1em;
  column-gap: 2em;
  padding: 1em;
}

.chip-icon-group {
  display: inline-flex;
  gap: 0.5em;
  align-items: center;
}
</style>
