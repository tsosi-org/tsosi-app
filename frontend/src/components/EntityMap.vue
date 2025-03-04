<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import * as L from "leaflet"
import Skeleton from "primevue/skeleton"
import {
  ref,
  onMounted,
  type Ref,
  nextTick,
  useTemplateRef,
  type App,
  type Component,
} from "vue"
import Loader from "./atoms/LoaderAtom.vue"
import {
  type EntityDetails,
  type DeepReadonly,
  getEntitySummary,
} from "@/singletons/ref-data"
import {
  parsePointCoordinates,
  getCountryCoordinates,
  getCountryLabel,
} from "@/utils/data-utils"
import { getEmitters, type Entity } from "@/singletons/ref-data"
import { type Feature } from "geojson"
import EntityTitleLogo from "@/components/EntityTitleLogo.vue"
import CountryItemList from "@/components/CountryItemList.vue"
import { createComponent } from "@/utils/dom-utils"
import InfoButtonAtom from "./atoms/InfoButtonAtom.vue"

export interface EntityMapProps {
  entity: DeepReadonly<EntityDetails>
  initPosition?: {
    lat: number
    lon: number
    zoom?: number
  }
}

const props = defineProps<EntityMapProps>()
// const tileBaseUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
// TODO: Check that it's actually OK to use carto basemaps
const tileBaseUrl =
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"

const loading = ref(true)
const mapElement = useTemplateRef("tsosi-map")
const mapData: Ref<Entity[] | null> = ref(null)
const layers: Ref<Record<string, L.FeatureGroup>> = ref({})
const plottedEntities: Ref<{ total: number; value: number } | null> = ref(null)
// Do not use a ref, it messes up some leaflet features
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
const countryIcon = L.divIcon({
  html: diamondSvg,
  iconSize: [12, 12],
  className: "map-icon diamond-icon",
})
const houseIcon = L.divIcon({
  html: houseSvg,
  iconSize: [18, 18],
  className: "map-icon house-icon",
})
const circleIcon = L.divIcon({
  html: circleSvg,
  iconSize: [10, 10],
  className: "map-icon circle-icon",
})
onMounted(async () => {
  await onInit()
  await getData()
  await updateMarkers()
})

async function onInit() {
  await nextTick()

  const initLat = props.initPosition?.lat ?? 30
  const initLon = props.initPosition?.lon ?? -10
  const initZoom = props.initPosition?.zoom ?? 3
  const options: L.MapOptions = {
    center: L.latLng(initLat, initLon),
    zoom: initZoom,
  }
  const mapObject = L.map(mapElement.value as HTMLElement, options)
  L.tileLayer(tileBaseUrl, {
    maxZoom: 12,
    minZoom: 1,
    attribution:
      '&copy; <a target="_blank" rel="noopener noreferrer" href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a target="_blank" rel="noopener noreferrer" href="https://carto.com/attribution">CARTO</a>',
  }).addTo(mapObject)
  mapObject.invalidateSize()

  map = mapObject
}

async function getData() {
  mapData.value = await getEmitters(props.entity.id)
}

/**
 * Add geoJSON layers to the map from the mapData
 */
async function updateMarkers() {
  loading.value = true
  if (!map || !mapData.value) {
    return
  }
  const newLayers: Record<string, L.FeatureGroup> = {}
  const emitterRatio = {
    total: mapData.value.length,
    value: 0,
  }

  const emitterFeatures: Feature[] = []
  const emitterCountries: { [code: string]: Entity[] } = {}
  for (const item of mapData.value) {
    let feature: Feature | null = null
    const coordinates = parsePointCoordinates(item.coordinates)
    if (coordinates) {
      feature = {
        type: "Feature",
        properties: {
          ...item,
        },
        geometry: {
          type: "Point",
          coordinates: [coordinates.lon, coordinates.lat],
        },
      }
      emitterFeatures.push(feature)
      emitterRatio.value += 1
    } else if (item.country) {
      if (!(item.country in emitterCountries)) {
        emitterCountries[item.country] = []
      }
      emitterCountries[item.country].push(item)
    }
  }
  if (emitterFeatures) {
    newLayers.emitters = L.geoJSON(emitterFeatures, {
      pointToLayer: (feature, latlng) =>
        // L.marker(latlng, {
        //   icon: circleIcon,
        // }),
        L.circleMarker(latlng, {
          color: "#216d95",
          weight: 1,
          fillColor: "#216d95",
          fillOpacity: 0.5,
          radius: 5,
        }),
      onEachFeature: (feature, layer) =>
        layer.bindPopup(() => {
          const mountElement = document.createElement("div")
          const popup = createPopup(EntityTitleLogo, mountElement, {
            entity: getEntitySummary(feature.properties.id),
          })
          layer.on("popupclose", () => cleanPopup(popup))
          return mountElement
        }),
    })
  }
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
      emitterRatio.value += emitterCountries[key].length
    }
    if (countryFeatures.length) {
      newLayers.countries = L.geoJSON(countryFeatures, {
        pointToLayer: (feature, latlng) =>
          L.marker(latlng, {
            icon: countryIcon,
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
  const entityCoordinates = parsePointCoordinates(props.entity.coordinates)
  if (entityCoordinates) {
    const infraFeature: Feature = {
      type: "Feature",
      properties: {
        ...props.entity,
      },
      geometry: {
        type: "Point",
        coordinates: [entityCoordinates.lon, entityCoordinates.lat],
      },
    }

    newLayers.infra = L.geoJSON(infraFeature, {
      pointToLayer: (feature, latlng) =>
        L.marker(latlng, {
          icon: houseIcon,
          opacity: 0.95,
        }),
      onEachFeature: (feature, layer) => {
        layer.bindPopup(() => {
          const mountElement = document.createElement("div")
          const popup = createPopup(EntityTitleLogo, mountElement, {
            entity: props.entity,
          })
          layer.on("popupclose", () => cleanPopup(popup))
          return mountElement
        })
      },
    })
  }
  for (const layer of Object.values(newLayers)) {
    layer.addTo(map)
  }
  layers.value = newLayers
  plottedEntities.value = emitterRatio
  loading.value = false
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
</script>

<template>
  <div class="map-wrapper">
    <div class="map-header">
      <h2 class="map-title">Funder locations</h2>
      <span v-if="plottedEntities">
        Showing {{ plottedEntities.value }} out of
        {{ plottedEntities.total }} funders ({{
          (
            Math.round(
              (10 * (100 * plottedEntities.value)) / plottedEntities.total,
            ) / 10
          ).toString()
        }}%)
      </span>
      <Skeleton v-else width="10em" border-radius="5px" height="1em"></Skeleton>
    </div>
    <div v-show="!loading" class="map-legend">
      <div v-if="layers.infra" class="legend-item">
        <div class="legend-icon house-icon" v-html="houseSvg"></div>
        <span>Supported Infrastructure</span>
      </div>
      <div v-if="layers.countries" class="legend-item">
        <div class="legend-icon diamond-icon" v-html="diamondSvg"></div>
        <span>
          Countries
          <InfoButtonAtom>
            <template #default>
              <span>
                Gather all funders from the given country without a precise
                location information.
              </span>
            </template>
          </InfoButtonAtom>
        </span>
      </div>
      <div v-if="layers.emitters" class="legend-item">
        <div class="legend-icon circle-icon" v-html="circleSvg"></div>
        <span>Individual Funders</span>
      </div>
    </div>
    <div v-show="loading" class="map-legend">
      <div class="legend-item">
        <Skeleton shape="circle" size="1rem"></Skeleton>
        <Skeleton width="10ch" border-radius="3px" height="0.9rem"></Skeleton>
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
    <div class="map-container">
      <div v-show="loading" class="loader-wrapper">
        <Loader width="200px"></Loader>
      </div>
      <div class="map" ref="tsosi-map"></div>
    </div>
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

.map-legend {
  display: flex;
  row-gap: 0.5em;
  column-gap: 1.5em;
  justify-content: center;
}

.legend-item {
  display: flex;
  font-size: 0.9rem;
  align-items: center;
  gap: 0.5em;

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
  fill: #e7a824;
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
</style>
