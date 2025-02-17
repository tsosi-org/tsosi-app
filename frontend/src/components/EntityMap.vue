<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import * as L from "leaflet"
import { ref, onMounted, type Ref, nextTick, useTemplateRef } from "vue"
import Loader from "./atoms/LoaderAtom.vue"
import { type EntityDetails, type DeepReadonly } from "@/singletons/ref-data"
import { parsePointCoordinates } from "@/utils/data-utils"
import { getEmitters, type EntityCoordinates } from "@/singletons/ref-data"

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
// const map: Ref<L.Map | null> = ref(null)
const mapElement = useTemplateRef("tsosi-map")
const mapData: Ref<EntityCoordinates[] | null> = ref(null)
const layers: Record<string, L.FeatureGroup> = {}
// Do not use a ref, it messes up some leaflet features
let map: L.Map | null = null

onMounted(async () => {
  await onInit()
  await getData()
  await updateMarkers()
})

async function onInit() {
  loading.value = false
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
      '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attribution">CARTO</a>',
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
  if (!map || !mapData.value) {
    return
  }
  const emitterFeatures = []
  for (const item of mapData.value) {
    let feature = null
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
    }
  }
  if (emitterFeatures.length) {
    layers.emitters = L.geoJSON(emitterFeatures, {
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          color: "#216d95",
          weight: 1,
          fillColor: "#216d95",
          fillOpacity: 0.5,
          radius: 5,
        }),
      onEachFeature: (feature, layer) =>
        layer.bindPopup(feature.properties.name),
    })
    // .on("click", (event) => {
    //  console.log("clicked event")
    // console.log(event)
    // })
  }
  const entityCoordinates = parsePointCoordinates(props.entity.coordinates)
  if (entityCoordinates) {
    const infraFeature = {
      type: "Feature",
      properties: {
        ...props.entity,
      },
      geometry: {
        type: "Point",
        coordinates: [entityCoordinates.lon, entityCoordinates.lat],
      },
    }

    layers.infra = L.geoJSON(infraFeature, {
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          color: "#e57126",
          weight: 1,
          fillColor: "#e57126",
          fillOpacity: 0.5,
          radius: 10,
        }),
      onEachFeature: (feature, layer) =>
        layer.bindPopup(feature.properties.name),
    })
  }
  for (const layer of Object.values(layers)) {
    layer.addTo(map)
  }
}
</script>

<template>
  <div class="map-container">
    <Loader v-show="loading" width="200px"></Loader>
    <div class="map" ref="tsosi-map"></div>
  </div>
</template>

<style>
.map-container {
  position: relative;
  height: 40rem;
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
</style>
