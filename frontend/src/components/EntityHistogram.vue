<script setup lang="ts">
import Chart from "primevue/chart"
import { ref, watch, onMounted, computed, useTemplateRef, type Ref } from "vue"
import Select from "primevue/select"
import Checkbox from "primevue/checkbox"
import { type TooltipItem } from "chart.js"

import CurrencySelector from "./CurrencySelector.vue"

import Loader from "@/components/atoms/LoaderAtom.vue"
import {
  getAnalytics,
  type Analytic,
  type Entity,
  type DeepReadonly,
} from "@/singletons/ref-data"
import {
  selectedCurrency,
  defaultCurrency,
  originalCurrency,
  setSelectedCurrency,
} from "@/singletons/currencyStore"
import { getCountryRegion, exportPNG } from "@/utils/data-utils"
import { type DataFieldProps, exportCSV, exportJSON } from "@/utils/data-utils"
import MenuButtonAtom from "@/components/atoms/MenuButtonAtom.vue"


export interface EntityHistogramProps {
  entity: DeepReadonly<Entity>
  disableExport?: boolean
}

interface ChartSerie {
  type: string
  data: any[]
  label: string
  backgroundColor?: string
  stack?: string | number
}

interface ChartData {
  labels: number[]
  datasets: ChartSerie[]
}

const metricOptions = [
  {
    code: "sum",
    name: "Sum of funding",
  },
  {
    code: "count",
    name: "Count of funding",
  },
]
const props = defineProps<EntityHistogramProps>()
const rawData: Ref<Analytic[] | null> = ref(null)
const dataLoaded = ref(false)
const loading = ref(true)
const chartData: Ref<ChartData | undefined> = ref()
const chartOptions: Ref<object | undefined> = ref()
const chartTitle =
  "Distribution of funding by year of receipt and continent of supporters"
const yAxisTitle = computed(() =>
  metric.value.code == "sum"
    ? `Total amount of funding (${selectedCurrency.value.id})`
    : "Total number of funding",
)

// Chart controls
const metric = ref(metricOptions[0])
const stacked: Ref<boolean> = ref(false)

const chartComponent = useTemplateRef("chart")

onMounted(async () => {
  await loadData()
  if (selectedCurrency.value.id == originalCurrency.id) {
    setSelectedCurrency(defaultCurrency.id)
  }
  updateChart()
})

watch(selectedCurrency, () => {
  if (selectedCurrency.value.id == originalCurrency.id) {
    return
  }
  updateChart()
})
watch(metric, updateChart)
watch(stacked, updateChart)

async function loadData() {
  // await new Promise((r) => setTimeout(r, 800))
  rawData.value = await getAnalytics(props.entity.id)
  dataLoaded.value = true
}

function updateChart() {
  if (!dataLoaded.value) {
    console.warn("Chart is trying to draw before data was loaded")
    return
  }
  // Group data by region/continent
  loading.value = true
  if (rawData.value == null) {
    return
  }

  // Group values per region
  const labels: number[] = []
  const dataBuckets: { [id: string]: { [year: number]: number } } = {}
  for (const item of rawData.value) {
    let key = "Unknown"
    const year = item.year
    let value = 0
    if (metric.value.code == "sum") {
      value = item.data[selectedCurrency.value.id] || value
    } else if (metric.value.code == "count") {
      value = item.data["count"] || value
    }
    if (item.country) {
      key = getCountryRegion(item.country)
    }
    if (!(key in dataBuckets)) {
      dataBuckets[key] = {}
    }
    if (!(year in dataBuckets[key])) {
      dataBuckets[key][year] = 0
    }
    dataBuckets[key][year] += value
    if (!labels.includes(year)) {
      labels.push(year)
    }
  }

  // Generate series for Chart.js
  labels.sort()
  const datasets: ChartSerie[] = []
  for (const key of Object.keys(dataBuckets)) {
    const bucket = dataBuckets[key]
    datasets.push({
      type: "bar",
      data: labels.map((label) => bucket[label] || null),
      label: key,
    })
  }
  datasets.sort((a, b) => (a.label < b.label ? -1 : 1))
  colorIndex = 0
  datasets.forEach((set) => {
    set["backgroundColor"] = set.label == "Unknown" ? "#9ca3af" : nextColor()
  })
  if (stacked.value) {
    datasets.forEach((set, ind) => {
      set["stack"] = `Stack ${ind}`
    })
  }
  // Set chartData and chartOptions
  chartData.value = {
    labels: labels,
    datasets: datasets,
  }
  chartOptions.value = getChartOptions()
  loading.value = false
}

function getChartOptions() {
  return {
    // maintainAspectRatio: false,
    // aspectRatio: 2.5,
    maintainAspectRatio: false,
    aspectRatio: 0.8,
    responsive: true,
    // skipNull: true,
    interaction: {
      intersect: false,
      mode: "index",
    },
    scales: {
      x: {
        stacked: true,
        title: {
          display: true,
          text: "Year of receipt of funding",
        },
      },
      y: {
        stacked: true,
        title: {
          display: true,
          text: yAxisTitle.value,
        },
      },
    },
    plugins: {
      tooltip: {
        callbacks: {
          title: (ttItems: TooltipItem<"bar">[]) =>
            `${ttItems[0].label}: ${ttItems.reduce((acc, val) => acc + val.parsed.y, 0).toLocaleString()}`,
        },
      },
    },
  }
}

function refColors(): string[] {
  const blue = ["#216d95", "#3d9bcc", "#0e5378"]
  const orange = ["#e57126", "#f58d49", "#a84200"]
  const green = ["#b3d4c9", "#4dbd98", "#1f805f"]
  const yellow = ["#e7a824", "#f0c66e", "#ad7602"]
  const colors = []
  for (let i = 0; i < blue.length; i++) {
    colors.push(blue[i])
    colors.push(green[i])
    colors.push(orange[i])
    colors.push(yellow[i])
  }
  return colors
}

let colorIndex = 0

function nextColor() {
  const ref = refColors()
  if (colorIndex > ref.length - 1) {
    colorIndex = 0
  }
  const color = ref[colorIndex]
  colorIndex += 1
  return color
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
  {
    label: "Export PNG",
    icon: ["fas", "download"],
    command: () => downloadPNG(),
  },
]

function getFileName(): string {
  const baseName = props.entity.name.replace(/\s+/g, "_")
  const chartTitleClean = chartTitle.replace(/\s+/g, "_")
  return `TSOSI_${baseName}_${chartTitleClean}`
}

async function downloadPNG() {
  const innerChart = chartComponent.value?.getChart()
  if (!innerChart) {
    return
  }
  const image = innerChart.toBase64Image()
  exportPNG(image, getFileName())
}

async function downloadData(format: "json" | "csv") {
  if (!chartData.value) {
    console.warn("Chart: No data to export!")
    return
  }

  const exportData = []

  // Convert the column-like data into row-like data for export
  for (let i = 0; i < chartData.value.labels.length; i++) {
    const dataItem: Record<string, any> = {
      x: chartData.value.labels[i],
    }
    chartData.value.datasets.forEach(
      (dataset, key) => (dataItem[key.toString()] = dataset.data[i]),
    )
    exportData.push(dataItem)
  }
  // Create DataField config
  const fields: DataFieldProps[] = []
  fields.push({
    id: "x",
    title: "Year of receipt of funding",
    field: "x",
    type: "number",
  })
  chartData.value.datasets.forEach((dataset, key) =>
    fields.push({
      id: key.toString(),
      title: dataset.label,
      field: key.toString(),
      type: "number",
    }),
  )
  if (format == "csv") {
    exportCSV(fields, exportData, getFileName())
    return
  }
  exportJSON(fields, exportData, getFileName())
}
</script>

<template>
  <div class="chart-wrapper">
    <div class="chart-header">
      <h2 class="chart-title">
        {{ chartTitle }}
      </h2>
    </div>

    <div class="chart-container">
      <Loader v-if="loading" width="200px" />
      <Chart
        v-show="!loading"
        ref="chart"
        class="chart"
        type="bar"
        :data="chartData"
        :options="chartOptions"
      />
    </div>

    <div class="chart-controls">
      <div class="check-box-wrapper">
        <Checkbox v-model="stacked" inputId="histogramStacked" binary />
        <label for="histogramStacked"> Grouped </label>
      </div>
      <Select v-model="metric" :options="metricOptions" optionLabel="name" />
      <CurrencySelector />
      <template v-if="!props.disableExport">
        <MenuButtonAtom
          :id="`histogram-export-menu-${props.entity.id}`"
          :button="{
            id: `histogram-export-button-${props.entity.id}`,
            label: 'Export',
            type: 'action',
            icon: ['fas', 'download'],
          }"
          :items="exportItems"
        />
      </template>
    </div>

    <div class="chart-description">
      <div style="padding: 0 min(2vw, 2em)">
        This graph shows all the funding received by the infrastructure,
        distributed by year of receipt and by continent of the supporters. The
        date and amount of funding are received from the infrastructure, while
        the continent of the supporters comes from ROR and Wikidata.
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  min-width: 300px;

  & > * {
    margin-top: 1.5rem;
  }

  & > *:first-child {
    margin-top: unset;
  }
}
.chart-header {
  text-align: center;
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  gap: 0.8em;
  justify-content: end;
}

.check-box-wrapper {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.25em;
}

.chart-title {
  font-weight: 900;
}

.chart-container {
  position: relative;
  height: 30rem;
}

.chart {
  height: 30rem;
}

.chart-description {
  margin-left: auto;
  margin-right: auto;
  width: fit-content;
}
</style>
