<script setup lang="ts">
import Chart from "primevue/chart"
import Loader from "@/components/atoms/LoaderAtom.vue"
import { ref, watch, onMounted, computed, useTemplateRef, type Ref } from "vue"
import { getAnalytics, type Analytic } from "@/singletons/ref-data"
import { selectedCurrency } from "@/singletons/currencyStore"
import { getCountryRegion } from "@/utils/data-utils"
import Select from "primevue/select"
import Checkbox from "primevue/checkbox"
import CurrencySelector from "./CurrencySelector.vue"
import { type DataFieldProps, exportCSV, exportJSON } from "@/utils/data-utils"
import Button from "primevue/button"
import Menu from "primevue/menu"
import { type TooltipItem } from "chart.js"

export interface EntityHistogramProps {
  entityId: string
  exportTitle?: string
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
    name: "Metric: Sum",
  },
  {
    code: "count",
    name: "Metric: Count",
  },
]
const props = defineProps<EntityHistogramProps>()
const rawData: Ref<Analytic[] | null> = ref(null)
const dataLoaded = ref(false)
const loading = ref(true)
const chartData: Ref<ChartData | undefined> = ref()
const chartOptions: Ref<object | undefined> = ref()
const chartTitle = computed(() =>
  metric.value.code == "sum"
    ? `Total value (${selectedCurrency.value.id})`
    : "Number of transferts",
)

// Chart controls
const metric = ref(metricOptions[0])
const stacked: Ref<boolean> = ref(false)

onMounted(async () => {
  await loadData()
  updateChart()
})

watch(selectedCurrency, updateChart)
watch(metric, updateChart)
watch(stacked, updateChart)

async function loadData() {
  // await new Promise((r) => setTimeout(r, 800))
  rawData.value = await getAnalytics(props.entityId)
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
    let color = "#9ca3af"
    if (key != "Unknown") {
      color = nextColor()
    }

    datasets.push({
      type: "bar",
      data: labels.map((label) => bucket[label] || null),
      label: key,
      backgroundColor: color,
    })
  }
  if (stacked.value) {
    datasets.forEach((set, ind) => {
      set["stack"] = `Stack ${ind}`
    })
  }
  // Set chartData and chartOptions
  chartData.value = {
    labels: labels,
    datasets: datasets.sort((a, b) => (a.label < b.label ? -1 : 1)),
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
          text: "Year",
        },
      },
      y: {
        stacked: true,
        title: {
          display: true,
          text: chartTitle,
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
  return ["#36a2eb", "#ff6384", "#4bc0c0", "#ff9f40", "#9966ff", "#ffcd56"]
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

const exportMenu = useTemplateRef("export-menu")

const exportItems = [
  {
    label: "Export CSV",
    icon: "download",
    command: () => download("csv"),
  },
  {
    label: "Export JSON",
    icon: "download",
    command: () => download("json"),
  },
]

async function download(format: "json" | "csv") {
  if (!chartData.value) {
    console.warn("Chart: No data to export!")
    return
  }
  const chartTitleClean = chartTitle.value.replace(/\s+/g, "_")
  const fileName = `TSOSI_${chartTitleClean}`
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
    title: "Year",
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
    exportCSV(fields, exportData, fileName)
    return
  }
  exportJSON(fields, exportData, fileName)
}

function toggleExportMenu(event: Event) {
  exportMenu.value!.toggle(event)
}
</script>

<template>
  <div class="chart-wrapper">
    <Loader v-if="loading" width="200px" />
    <div class="chart-header">
      <h2 class="chart-title">
        <template v-if="metric.code == 'sum'">
          Overall funding per year in {{ selectedCurrency.name }}
        </template>
        <template v-else> Number of transferts per year </template>
      </h2>
      <div class="chart-controls">
        <div class="check-box-wrapper">
          <Checkbox v-model="stacked" inputId="histogramStacked" binary />
          <label for="histogramStacked"> Grouped </label>
        </div>
        <Select v-model="metric" :options="metricOptions" optionLabel="name" />
        <CurrencySelector />
        <template v-if="!props.disableExport">
          <Button
            label="Export"
            type="button"
            @click="toggleExportMenu"
            aria-haspopup="true"
            :aria-controls="`histogram-export-menu-${props.entityId}`"
          >
            <template #icon>
              <font-awesome-icon icon="download" />
            </template>
          </Button>
          <Menu
            ref="export-menu"
            :id="`histogram-export-menu-${props.entityId}`"
            :model="exportItems"
            :popup="true"
          >
            <template #itemicon="{ item }">
              <font-awesome-icon :icon="item.icon" />
            </template>
          </Menu>
        </template>
      </div>
    </div>
    <Chart
      v-show="!loading"
      type="bar"
      :data="chartData"
      :options="chartOptions"
      class="chart"
    />
  </div>
</template>

<style scoped>
.chart-header {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  row-gap: 1em;
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  gap: 0.8em;
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

.chart {
  height: 30rem;
  margin-top: 1.5rem;
}
</style>
