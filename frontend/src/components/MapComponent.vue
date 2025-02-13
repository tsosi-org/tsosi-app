<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import * as L from "leaflet"
import { type GeoJsonObject } from "geojson"
import { ref, onMounted, type Ref, nextTick, useTemplateRef } from "vue"
import Loader from "./atoms/LoaderAtom.vue"
import { getCountries } from "@/singletons/ref-data"

const loading = ref(true)

const map: Ref<L.Map | null> = ref(null)
const mapElement = useTemplateRef("tsosi-map")

// This holds the geoJSON of country geometries
let countryData: GeoJsonObject | null = null
const selectedCountries = ref(["FR", "EN", "US", "AU", "RU"])
let countryOverlay: L.GeoJSON | null = null

async function onInit() {
  // @ts-expect-error Because
  countryData = await getCountries()

  loading.value = false
  await nextTick()

  const options: L.MapOptions = {
    center: L.latLng(30, -10),
    zoom: 3,
  }
  const mapObject = L.map(mapElement.value as HTMLElement, options)
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 10,
    attribution:
      '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapObject)
  mapObject.invalidateSize()

  map.value = mapObject
  // updateCountryOverlay()
  setTimeout(() => {
    selectedCountries.value = ["EN", "CA", "BR", "JP"]
  }, 1000)
}

/**
 * Update the country data and add it to the map and
 * replacing existing one, if any.
 */
function updateCountryOverlay(): void {
  if (!countryData || !map.value) {
    return
  }
  if (countryOverlay) {
    map.value.removeLayer(countryOverlay)
  }
  const options: L.GeoJSONOptions = {
    filter: (feature) =>
      selectedCountries.value.includes(feature.properties.iso_a2),
    style: () => {
      return {
        stroke: true,
        color: "#3388ff",
        weight: 1,
        fill: true,
        fillOpacity: 0.2,
        className: "country-svg",
        bubblingMouseEvents: false,
      }
    },
    onEachFeature: (feature, layer) => {
      layer.on("click", () =>
        console.log(`Clicked country ${feature.properties.iso_a2}`),
      )
      if (layer.hasOwnProperty("setStyle")) {
        layer.on("mouseover", () =>
          // @ts-expect-error Because
          layer.setStyle({ weight: 2, fillOpacity: 0.4 }),
        )
        layer.on("mouseout", () =>
          // @ts-expect-error Because
          layer.setStyle({ weight: 1, fillOpacity: 0.2 }),
        )
      }
    },
  }
  countryOverlay = L.geoJSON(countryData, options)
  countryOverlay.addTo(map.value)
}

// watch(selectedCountries, updateCountryOverlay)

onMounted(async () => {
  await onInit()
  updateCountryOverlay()
})
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
  height: calc(100vh - var(--header-height));
  width: 100%;

  .leaflet-tile-pane {
    filter: grayscale(100%) !important;
  }

  .map {
    width: 100%;
    height: 100%;
  }
}
</style>
