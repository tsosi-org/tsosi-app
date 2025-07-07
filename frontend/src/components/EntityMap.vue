<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import * as L from "leaflet"
import Skeleton from "primevue/skeleton"
import Accordion from "primevue/accordion"
import AccordionPanel from "primevue/accordionpanel"
import AccordionHeader from "primevue/accordionheader"
import AccordionContent from "primevue/accordioncontent"
import {
  ref,
  onMounted,
  watch,
  type Ref,
  nextTick,
  useTemplateRef,
  computed,
  type App,
  type Component,
} from "vue"
import Loader from "./atoms/LoaderAtom.vue"
import { getEntitySummary } from "@/singletons/ref-data"
import {
  parsePointCoordinates,
  getCountryCoordinates,
  getCountryLabel,
  exportCSV,
  exportJSON,
  type DataFieldProps,
} from "@/utils/data-utils"
import { type Entity } from "@/singletons/ref-data"
import { type Feature } from "geojson"
import EntityTitleLogo from "@/components/EntityTitleLogo.vue"
import CountryItemList from "@/components/CountryItemList.vue"
import { createComponent } from "@/utils/dom-utils"
import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"
import MenuButtonAtom from "@/components/atoms/MenuButtonAtom.vue"
import { isDesktop } from "@/composables/useMediaQuery"

export interface EntityMapProps {
  id: string
  infrastructures?: Entity[]
  supporters: Entity[]
  title?: string
  dataLoaded?: boolean
  exportTitleBase?: string
  disableExport?: boolean
  showIconLegend?: boolean
  showLegend?: boolean
}

const props = defineProps<EntityMapProps>()
// const tileBaseUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
// TODO: Check that it's actually OK to use carto basemaps
const tileBaseUrl =
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"

const loading = ref(true)
const mapElement = useTemplateRef("tsosi-map")
const layers: Ref<Record<string, L.FeatureGroup>> = ref({})
const plottedSupporters: Ref<{
  total: number
  value: number
  countries: number
} | null> = ref(null)
const scalingRatio = computed(() => (isDesktop.value ? 1 : 1.25))

// Do not use a ref, it messes up some leaflet features
let layerGroup: L.LayerGroup | null = null
let map: L.Map | null = null
const houseSvg = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512">
    <path d="M575.8 255.5c0 18-15 32.1-32 32.1l-32 0 .7 160.2c0 2.7-.2 5.4-.5 8.1l0 16.2c0 22.1-17.9 40-40 40l-16 0c-1.1 0-2.2 0-3.3-.1c-1.4 .1-2.8 .1-4.2 .1L416 512l-24 0c-22.1 0-40-17.9-40-40l0-24 0-64c0-17.7-14.3-32-32-32l-64 0c-17.7 0-32 14.3-32 32l0 64 0 24c0 22.1-17.9 40-40 40l-24 0-31.9 0c-1.5 0-3-.1-4.5-.2c-1.2 .1-2.4 .2-3.6 .2l-16 0c-22.1 0-40-17.9-40-40l0-112c0-.9 0-1.9 .1-2.8l0-69.7-32 0c-18 0-32-14-32-32.1c0-9 3-17 10-24L266.4 8c7-7 15-8 22-8s15 2 21 7L564.8 231.5c8 7 12 15 11 24z"/>
  </svg>
`
const diamondSvg = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <path d="M284.3 11.7c-15.6-15.6-40.9-15.6-56.6 0l-216 216c-15.6 15.6-15.6 40.9 0 56.6l216 216c15.6 15.6 40.9 15.6 56.6 0l216-216c15.6-15.6 15.6-40.9 0-56.6l-216-216z"/>
  </svg>
`
const circleSvg = `
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <path stroke-linecap="round" stroke-linejoin="round" d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512z"/>
  </svg>
`
const countryIcon = computed(() =>
  L.divIcon({
    html: diamondSvg,
    iconSize: [12 * scalingRatio.value, 12 * scalingRatio.value],
    className: "map-icon diamond-icon",
  }),
)

const houseIcon = computed(() =>
  L.divIcon({
    html: houseSvg,
    iconSize: [18 * scalingRatio.value, 18 * scalingRatio.value],
    className: "map-icon house-icon",
  }),
)
// const circleIcon = L.divIcon({
//   html: circleSvg,
//   iconSize: [10, 10],
//   className: "map-icon circle-icon",
// })

onMounted(async () => {
  await onInit()
  await updateMarkers()
})

watch(props, async () => updateMarkers())
watch(isDesktop, async () => updateMarkers())

async function onInit() {
  await nextTick()

  const options: L.MapOptions = {
    maxBoundsViscosity: 1,
    // Having max bounds can cause issue with the popups, that may be out of
    // reach.
    // maxBounds: [
    //   [-89, -181],
    //   [89, 181],
    // ],
  }
  const mapObject = L.map(mapElement.value as HTMLElement, options)
  L.tileLayer(tileBaseUrl, {
    maxZoom: 18,
    minZoom: 1,
    attribution:
      '&copy; <a target="_blank" rel="noopener noreferrer" href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a target="_blank" rel="noopener noreferrer" href="https://carto.com/attribution">CARTO</a>',
  }).addTo(mapObject)
  mapObject.invalidateSize()

  map = mapObject
  layerGroup = L.layerGroup().addTo(map)
}

/**
 * Add geoJSON layers to the map from the mapData
 */
async function updateMarkers() {
  loading.value = true
  await nextTick()
  if (!map || !layerGroup || !props.dataLoaded) {
    return
  }
  // Clean the map
  layerGroup.clearLayers()
  await nextTick()

  // Draw new layers
  const newLayers: Record<string, L.GeoJSON> = {}
  const emittersRecap = {
    total: props.supporters.length,
    value: 0,
    countries: new Set(
      props.supporters.map((e) => e.country).filter((c) => c != null),
    ).size,
  }
  // Construct individual emitters layer
  // We merge features with the exact same coordinates otherwise
  // they overlap on the map.
  const emitterFeatures: { [code: string]: Feature } = {}
  const emitterCountries: { [code: string]: Entity[] } = {}
  for (const item of props.supporters) {
    const coordinates = parsePointCoordinates(item.coordinates)
    if (coordinates) {
      if (item.coordinates! in emitterFeatures) {
        emitterFeatures[item.coordinates!].properties?.items.push(item.id)
      } else {
        emitterFeatures[item.coordinates!] = {
          type: "Feature",
          properties: {
            items: [item.id],
          },
          geometry: {
            type: "Point",
            coordinates: [coordinates.lon, coordinates.lat],
          },
        }
      }
      emittersRecap.value += 1
    } else if (item.country) {
      if (!(item.country in emitterCountries)) {
        emitterCountries[item.country] = []
      }
      emitterCountries[item.country].push(item)
    }
  }
  if (emitterFeatures) {
    newLayers.emitters = L.geoJSON(Object.values(emitterFeatures), {
      pointToLayer: (_, latlng) =>
        L.circleMarker(latlng, {
          color: "#216d95",
          weight: 1,
          fillColor: "#216d95",
          fillOpacity: 0.5,
          radius: 5 * scalingRatio.value,
        }),
      onEachFeature: (feature, layer) =>
        layer.bindPopup(
          () => {
            const mountElement = document.createElement("div")
            const items = feature.properties.items
            if (items.length > 1) {
              const popup = createPopup(CountryItemList, mountElement, {
                title: undefined,
                entities: items
                  .map(getEntitySummary)
                  .filter((e: any) => e != null)
                  .sort((a: Entity, b: Entity) => (a.name < b.name ? -1 : 1)),
              })
              layer.on("popupclose", () => cleanPopup(popup))
              return mountElement
            } else {
              const popup = createPopup(EntityTitleLogo, mountElement, {
                entity: getEntitySummary(items[0]),
              })
              layer.on("popupclose", () => cleanPopup(popup))
              return mountElement
            }
          },
          {
            maxHeight: 300,
          },
        ),
    })
  }
  // Construct emitter countries layer
  if (Object.keys(emitterCountries).length) {
    const countryFeatures: Feature[] = []
    for (const key of Object.keys(emitterCountries)) {
      const countryCoordinates = getCountryCoordinates(key)
      if (!countryCoordinates) {
        continue
      }
      countryFeatures.push({
        type: "Feature",
        properties: {
          items: emitterCountries[key].map((e: Entity) => e.id),
          name: getCountryLabel(key),
        },
        geometry: {
          type: "Point",
          coordinates: [...countryCoordinates],
        },
      })
      emittersRecap.value += emitterCountries[key].length
    }
    if (countryFeatures.length) {
      newLayers.countries = L.geoJSON(countryFeatures, {
        pointToLayer: (feature, latlng) =>
          L.marker(latlng, {
            icon: countryIcon.value,
            opacity: 0.9,
          }),
        onEachFeature: (feature, layer) =>
          layer.bindPopup(
            () => {
              const mountElement = document.createElement("div")
              const popup = createPopup(CountryItemList, mountElement, {
                title: feature.properties.name,
                entities: feature.properties.items
                  .map(getEntitySummary)
                  .filter((e: any) => e != null)
                  .sort((a: Entity, b: Entity) => (a.name < b.name ? -1 : 1)),
              })
              layer.on("popupclose", () => cleanPopup(popup))
              return mountElement
            },
            {
              maxHeight: 300,
            },
          ),
      })
    }
  }
  // Construct infrastructures layers
  const infraFeatures: Feature[] = []
  for (const item of props.infrastructures || []) {
    const coordinates = parsePointCoordinates(item.coordinates)
    if (!coordinates) {
      continue
    }
    const feature: Feature = {
      type: "Feature",
      properties: {
        id: item.id,
      },
      geometry: {
        type: "Point",
        coordinates: [coordinates.lon, coordinates.lat],
      },
    }
    infraFeatures.push(feature)
  }
  if (infraFeatures.length) {
    newLayers.infra = L.geoJSON(infraFeatures, {
      pointToLayer: (_, latlng) =>
        L.marker(latlng, {
          icon: houseIcon.value,
          opacity: 0.95,
        }),
      onEachFeature: (feature, layer) => {
        layer.bindPopup(() => {
          const mountElement = document.createElement("div")
          const popup = createPopup(EntityTitleLogo, mountElement, {
            entity: getEntitySummary(feature.properties.id),
          })
          layer.on("popupclose", () => cleanPopup(popup))
          return mountElement
        })
      },
    })
  }
  for (const layer of Object.values(newLayers)) {
    layer.addTo(layerGroup)
  }
  layers.value = newLayers
  plottedSupporters.value = emittersRecap
  loading.value = false
  const bonds = L.latLngBounds([])
  Object.values(layers.value).forEach((group) =>
    bonds.extend(group.getBounds()),
  )
  map.fitBounds(bonds)
}

function createPopup(
  component: Component,
  mountElement: HTMLElement,
  props?: Record<string, unknown>,
) {
  return createComponent(component, mountElement, props)
}

function cleanPopup(element: App) {
  setTimeout(() => {
    element.unmount()
  }, 400)
}

const exportItems = [
  {
    label: "Export CSV",
    icon: ["fas", "download"],
    command: () => downloadData("csv"),
  },
  {
    label: "Export JSON",
    icon: ["fas", "download"],
    command: () => downloadData("json"),
  },
]

function getFileName(): string {
  let baseName = "TSOSI"
  if (props.exportTitleBase) {
    baseName += "_"
    baseName += props.exportTitleBase.replace(/\s+/g, "_")
  }
  if (props.title) {
    baseName += "_"
    baseName += props.title.replace(/\s+/g, "_")
  }
  return baseName
}

function downloadData(format: "json" | "csv") {
  if (!props.dataLoaded || props.supporters.length == 0) {
    return
  }
  const exportData = []

  for (const item of props.supporters) {
    const coordinates = parsePointCoordinates(item.coordinates)
    exportData.push({
      id: item.id,
      name: item.name,
      latitude: coordinates?.lat,
      longitude: coordinates?.lon,
      country: item.country,
    })
  }

  const fields: DataFieldProps[] = [
    {
      id: "id",
      title: "id",
      field: "id",
      type: "string",
    },
    {
      id: "name",
      title: "name",
      field: "name",
      type: "string",
    },
    {
      id: "latitude",
      title: "latitude",
      field: "latitude",
      type: "number",
    },
    {
      id: "longitude",
      title: "longitude",
      field: "longitude",
      type: "number",
    },
    {
      id: "country",
      title: "country",
      field: "country",
      type: "country",
    },
  ]
  const fileName = getFileName()
  if (format == "csv") {
    exportCSV(fields, exportData, fileName)
    return
  }
  exportJSON(fields, exportData, fileName)
}

const legendDt = {
  header: {
    background: "transparent",
    active: {
      background: "transparent",
      hover: { background: "transparent" },
    },
    hover: { background: "transparent" },
  },
  content: {
    background: "transparent",
  },
}
</script>

<template>
  <div class="map-wrapper" :class="{ desktop: isDesktop }">
    <div class="map-header" v-if="props.title">
      <h2 class="map-title">{{ props.title }}</h2>
      <span v-if="plottedSupporters">
        {{ plottedSupporters.total }} supporters from
        {{ plottedSupporters.countries }} different countries
      </span>
      <Skeleton
        v-else
        width="10em"
        border-radius="5px"
        height="1em"
        style="display: inline-block"
      ></Skeleton>
    </div>

    <div class="map-container">
      <div v-show="loading" class="loader-wrapper">
        <Loader width="200px"></Loader>
      </div>
      <div class="map" ref="tsosi-map"></div>
    </div>

    <Accordion
      :value="props.showLegend ? '0' : undefined"
      :dt="legendDt"
      style="margin-top: 1em"
    >
      <AccordionPanel value="0">
        <AccordionHeader
          :pt="{ toggleicon: { style: 'position: absolute; left: 4px;' } }"
        >
          <div
            style="
              display: flex;
              width: 100%;
              margin-left: 1rem;
              justify-content: space-between;
            "
          >
            <h2>Legend</h2>
            <div v-if="!props.disableExport" class="map-export-menu">
              <MenuButtonAtom
                :id="`${props.id}-export-menu`"
                :button="{
                  id: `${props.id}-export-button`,
                  label: 'Export',
                  type: 'action',
                  icon: ['fas', 'download'],
                }"
                :items="exportItems"
              />
            </div>
          </div>
        </AccordionHeader>
        <AccordionContent>
          <div class="map-description">
            <div v-if="props.showIconLegend" style="position: relative">
              <div v-show="!loading" class="map-legend">
                <div v-if="layers.emitters" class="legend-item">
                  <div class="legend-icon circle-icon" v-html="circleSvg"></div>
                  <span>Individual supporters</span>
                </div>
                <div v-if="layers.countries" class="legend-item">
                  <div
                    class="legend-icon diamond-icon"
                    v-html="diamondSvg"
                  ></div>
                  <span>
                    Countries
                    <InfoButtonAtom>
                      <template #popup>
                        <span>
                          Gather all funders from the given country without a
                          precise location information.
                        </span>
                      </template>
                    </InfoButtonAtom>
                  </span>
                </div>
                <div v-if="layers.infra" class="legend-item">
                  <div class="legend-icon house-icon" v-html="houseSvg"></div>
                  <span>Supported infrastructures</span>
                </div>
              </div>

              <div
                v-if="props.showIconLegend"
                v-show="loading"
                class="map-legend"
              >
                <div class="legend-item">
                  <Skeleton shape="circle" size="1rem"></Skeleton>
                  <Skeleton
                    width="10ch"
                    border-radius="3px"
                    height="0.9rem"
                  ></Skeleton>
                </div>
                <div class="legend-item">
                  <Skeleton shape="circle" size="1rem"></Skeleton>
                  <Skeleton width="10ch" border-radius="3px"></Skeleton>
                </div>
                <div class="legend-item">
                  <Skeleton shape="circle" size="1rem"></Skeleton>
                  <Skeleton width="10ch" border-radius="3px"></Skeleton>
                </div>
              </div>
            </div>

            <div style="margin: 0 auto; width: fit-content">
              <div>
                This world map represents the locations of all the entities that
                have financially contributed to the infrastructure. Supporters
                with a specific location are represented by circles, while those
                for which TSOSI only has information at the country level are
                represented by diamond shapes. The location data comes from ROR
                and Wikidata.
                <span v-if="plottedSupporters">
                  {{ plottedSupporters.value }} supporters out of
                  {{ plottedSupporters.total }} are included in the world map.
                </span>
                <Skeleton
                  v-else
                  width="10em"
                  border-radius="5px"
                  height="1em"
                  style="display: inline-block"
                ></Skeleton>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionPanel>
    </Accordion>
  </div>
</template>

<style>
.map-wrapper {
  position: relative;
  width: 100%;
}

.loader-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #88888836;
  z-index: 999;
}

.map-title {
  font-weight: 900;
}

.map-container {
  margin-top: 1rem;
  position: relative;
  height: 35rem;
  width: 100%;

  .map {
    width: 100%;
    height: 100%;
    border-radius: 10px;
  }
  /* .leaflet-tile-pane {
    filter: grayscale(100%) !important;
  } */
}

.map-header {
  text-align: center;
}
.map-legend {
  display: flex;
  flex-wrap: wrap;
  row-gap: 0.5em;
  column-gap: 1.5em;
  justify-content: center;
  margin: 1em 0;
}

.legend-item {
  display: flex;
  flex-wrap: nowrap;
  font-size: 0.9rem;
  align-items: center;
  gap: 0.5em;
  white-space: nowrap;
  & .map-icon {
    stroke-width: unset;
  }
}

.legend-icon {
  width: 1rem;
  height: 1rem;
}

.map-icon {
  stroke-width: 40;
}

.diamond-icon {
  fill: #216d95;
  fill-opacity: 0.8;
  /* fill: #e7a824; */
  stroke: #686868;
}

.house-icon {
  fill: #e57126;
  stroke: #686868;
}

.circle-icon {
  fill: #216d95;
  fill-opacity: 0.8;
  stroke-width: 10;
  stroke: #216d95;
}

.map-export-menu {
  text-align: center;
  display: inline-block;
  margin-right: 1.5em;
}

.map-description > * {
  margin-bottom: 1em;
}
</style>
