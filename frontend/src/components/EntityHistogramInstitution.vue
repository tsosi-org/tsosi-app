<script setup lang="ts">
import { Chart as ChartJS, type Plugin, type TooltipItem } from "chart.js"
import Chart from "primevue/chart"
import {
  computed,
  nextTick,
  onMounted,
  ref,
  useTemplateRef,
  watch,
  type Ref,
} from "vue"

import Loader from "@/components/atoms/LoaderAtom.vue"
import {
  defaultCurrency,
  originalCurrency,
  selectedCurrency,
  setSelectedCurrency,
} from "@/singletons/currencyStore"
import {
  type DeepReadonly,
  type Entity,
  type Transfer,
} from "@/singletons/ref-data"
import {
  exportCSV,
  exportJSON,
  exportPNG,
  type DataFieldProps,
} from "@/utils/data-utils"

interface ChartSerie {
  type: string
  data: any[]
  label: string
  backgroundColor?: string
  stack?: string | number
}

interface ChartData {
  labels: string[]
  datasets: ChartSerie[]
}

const props = defineProps<{
  entity: DeepReadonly<Entity>
  transfers: Transfer[]
  disableExport?: boolean
}>()
const rawData: Ref<Transfer[] | null> = ref(null)
const dataLoaded = ref(false)
const loading = ref(true)
const chartData: Ref<ChartData | undefined> = ref()
const chartOptions: Ref<object | undefined> = ref()
const chartTitle = `Distribution of supports by year and infrastructure`
const yAxisTitle = computed(
  () => `Total amount of funding (${selectedCurrency.value.id})`,
)
const entityIconsByLabel: Record<string, string> = {}
const legendIconImageCache = new Map<string, HTMLImageElement>()
const legendIconPointStyleCache = new Map<string, HTMLCanvasElement>()
const LEGEND_ICON_SIZE = 16
const LEGEND_COLOR_BOX_WIDTH = 16
const LEGEND_ICON_LEFT_GAP = 8
const LEGEND_ICON_LABEL_PREFIX = "        "
const chartPlugins: Plugin<"bar">[] = []

// Chart controls
const stacked: Ref<boolean> = ref(false)

const chartComponent = useTemplateRef("chart")

const legendIconsPlugin: Plugin<"bar"> = {
  id: "legendIcons",
  afterDraw: (chart) => {
    const ctx = chart.ctx
    const legend = (chart as any).legend
    if (!ctx || !legend?.legendItems || !legend?.legendHitBoxes) {
      return
    }

    const legendItems = legend.legendItems as Array<{ text?: string }>
    const hitBoxes = legend.legendHitBoxes as Array<{
      left?: number
      top?: number
      width: number
      height: number
      x?: number
      y?: number
    }>

    legendItems.forEach((item, index) => {
      const label = (item.text || "").trimStart()
      const iconUrl = entityIconsByLabel[label]
      if (!iconUrl) {
        return
      }

      const icon = getLegendIconPointStyle(iconUrl, chart)
      if (!icon) {
        return
      }

      const hitBox = hitBoxes[index]
      if (!hitBox) {
        return
      }

      const left = hitBox.left ?? hitBox.x
      const top = hitBox.top ?? hitBox.y
      if (left == null || top == null) {
        return
      }

      const x = left + LEGEND_COLOR_BOX_WIDTH + LEGEND_ICON_LEFT_GAP
      const y = top + (hitBox.height - LEGEND_ICON_SIZE) / 2
      ctx.drawImage(icon, x, y, LEGEND_ICON_SIZE, LEGEND_ICON_SIZE)
    })
  },
}

chartPlugins.push(legendIconsPlugin)

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
watch(stacked, updateChart)

async function loadData() {
  // await new Promise((r) => setTimeout(r, 800))
  rawData.value = props.transfers
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

  // Group values per infra
  const labels: string[] = []
  const amounts: { [id: string]: number } = {}
  const dataBuckets: { [id: string]: { [year: string]: number } } = {}
  for (const label of Object.keys(entityIconsByLabel)) {
    delete entityIconsByLabel[label]
  }
  for (const item of rawData.value) {
    let key = "Unknown"
    if (!item.amounts_clc) {
      continue
    }
    const year: string =
      item.date_clc.dateObj?.getUTCFullYear().toString() || "Unknown"
    let value = 0
    value = item.amounts_clc[selectedCurrency.value.id] || value
    if (item.recipient) {
      key = item.recipient.short_name || item.recipient.name || key
      if (item.recipient.icon) {
        entityIconsByLabel[key] = item.recipient.icon
      }
    }
    if (!(key in dataBuckets)) {
      dataBuckets[key] = {}
      amounts[key] = 0
    }
    if (!(year in dataBuckets[key])) {
      dataBuckets[key][year] = 0
    }
    dataBuckets[key][year] += value
    amounts[key] += value
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
  datasets.sort((a, b) => amounts[b.label] - amounts[a.label])
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

  // Force one post-render pass when the canvas is visible so legend icons paint immediately.
  void nextTick(() => {
    refreshChartWhenVisible()
  })
}

function refreshChartWhenVisible(attempt = 0) {
  const innerChart = chartComponent.value?.getChart() as ChartJS | undefined
  const canvas = innerChart?.canvas
  if (!innerChart || !canvas) {
    return
  }

  const isVisible =
    canvas.isConnected &&
    canvas.clientWidth > 0 &&
    canvas.clientHeight > 0 &&
    canvas.offsetParent !== null

  if (!isVisible && attempt < 10) {
    requestAnimationFrame(() => {
      refreshChartWhenVisible(attempt + 1)
    })
    return
  }

  innerChart.update("none")
}

function getChartOptions() {
  return {
    animation: false,
    maintainAspectRatio: false,
    aspectRatio: 0.8,
    responsive: true,
    scales: {
      x: {
        stacked: true,
        title: {
          display: true,
          text: "Year of funding",
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
      legend: {
        position: "left",
        align: "center",
        title: {
          display: true,
        },
        labels: {
          boxWidth: LEGEND_COLOR_BOX_WIDTH,
          padding: 14,
          generateLabels: (chart: ChartJS) => {
            const defaultLabels =
              ChartJS.defaults.plugins.legend.labels.generateLabels(chart)
            return defaultLabels.map((legendItem) => {
              const label = legendItem.text || ""
              if (!entityIconsByLabel[label]) {
                return legendItem
              }
              return {
                ...legendItem,
                text: `${LEGEND_ICON_LABEL_PREFIX}${label}`,
              }
            })
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (ttItem: TooltipItem<"bar">) => {
            const value = ttItem.parsed.y
            return value
              ? `${ttItem.dataset.label}: ${value.toLocaleString()} ${selectedCurrency.value.id}`
              : ""
          },
        },
      },
    },
  }
}

function getLegendIconPointStyle(
  iconUrl: string,
  chart: ChartJS,
): HTMLCanvasElement | undefined {
  let pointStyle = legendIconPointStyleCache.get(iconUrl)
  if (!pointStyle) {
    pointStyle = document.createElement("canvas")
    pointStyle.width = LEGEND_ICON_SIZE
    pointStyle.height = LEGEND_ICON_SIZE
    legendIconPointStyleCache.set(iconUrl, pointStyle)
  }

  let icon = legendIconImageCache.get(iconUrl)
  if (!icon) {
    const createdIcon = new Image()
    createdIcon.onload = () => {
      drawLegendIconPointStyle(pointStyle, createdIcon)
      refreshChartWhenVisible()
    }
    createdIcon.src = iconUrl
    legendIconImageCache.set(iconUrl, createdIcon)
    return undefined
  }

  if (!icon.complete || !icon.naturalWidth || !icon.naturalHeight) {
    return undefined
  }

  drawLegendIconPointStyle(pointStyle, icon)
  return pointStyle
}

function drawLegendIconPointStyle(
  pointStyle: HTMLCanvasElement,
  icon: HTMLImageElement,
) {
  const ctx = pointStyle.getContext("2d")
  if (!ctx || !icon.naturalWidth || !icon.naturalHeight) {
    return
  }

  ctx.clearRect(0, 0, LEGEND_ICON_SIZE, LEGEND_ICON_SIZE)
  const scale = Math.min(
    LEGEND_ICON_SIZE / icon.naturalWidth,
    LEGEND_ICON_SIZE / icon.naturalHeight,
  )
  const drawWidth = icon.naturalWidth * scale
  const drawHeight = icon.naturalHeight * scale
  const drawX = (LEGEND_ICON_SIZE - drawWidth) / 2
  const drawY = (LEGEND_ICON_SIZE - drawHeight) / 2
  ctx.drawImage(icon, drawX, drawY, drawWidth, drawHeight)
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
    <div class="chart-container">
      <Loader v-if="loading" width="200px" />
      <Chart
        v-show="!loading"
        ref="chart"
        class="chart"
        type="bar"
        :data="chartData"
        :options="chartOptions"
        :plugins="chartPlugins"
      />
    </div>
    <div class="chart-header">
      <h2 class="chart-title">
        {{ chartTitle }}
      </h2>
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
