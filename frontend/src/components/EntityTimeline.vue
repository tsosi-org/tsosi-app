<script setup lang="ts">
import type { Plugin, TooltipItem } from "chart.js"
import "chartjs-adapter-date-fns"
import Chart from "primevue/chart"
import {
  computed,
  nextTick,
  onMounted,
  ref,
  useTemplateRef,
  type Ref,
} from "vue"

import Loader from "@/components/atoms/LoaderAtom.vue"
import { selectedCurrency } from "@/singletons/currencyStore"
import { type Entity, type Transfer } from "@/singletons/ref-data"
import { exportPNG } from "@/utils/data-utils"

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

const props = defineProps<{
  entity: Entity
  transfers: Transfer[]
  entities: Entity[]
  disableExport?: boolean
}>()
const chartData: Ref<ChartData | undefined> = ref()
const chartOptions: Ref<object | undefined> = ref()
const loading = ref(true)
const chartTitle = `Dates of supports by infrastructure`
const chartComponent = useTemplateRef("chart")
const chartPlugins: Plugin<"scatter">[] = []
const chartContainerStyle = computed(() => {
  const minHeightPx = 360
  const perTickHeightPx = 44
  const verticalPaddingPx = 80
  const tickCount = Math.max(props.entities.length, 1)

  return {
    height: `${Math.max(minHeightPx, tickCount * perTickHeightPx + verticalPaddingPx)}px`,
  }
})

const iconCache = new Map<string, HTMLImageElement>()

function getOrderedEntities(): Entity[] {
  return [...props.entities].reverse()
}

function getEntityLabel(entity: Entity): string {
  return entity.short_name || entity.name
}

function refreshChartWhenVisible(attempt = 0) {
  const innerChart = chartComponent.value?.getChart()
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

const yTickIconsPlugin: Plugin<"scatter"> = {
  id: "yTickIcons",
  afterDraw: (chart) => {
    const yScale = chart.scales.y
    const ctx = chart.ctx
    if (!yScale || !ctx) {
      return
    }

    const orderedEntities = getOrderedEntities()
    const ticks = yScale.ticks
    if (!ticks || ticks.length === 0) {
      return
    }

    const iconSize = 16
    const iconGap = 1
    const tickPadding = Number(
      (yScale.options as { ticks?: { padding?: number } }).ticks?.padding || 0,
    )

    ticks.forEach((tick, tickIndex) => {
      const tickValue = Number(tick.value)
      if (!Number.isFinite(tickValue) || tickValue < 0) {
        return
      }

      const entity = orderedEntities[tickValue]
      if (!entity?.icon) {
        return
      }

      let img = iconCache.get(entity.icon)
      if (!img) {
        img = new Image()
        img.src = entity.icon
        img.onload = () => {
          refreshChartWhenVisible()
        }
        iconCache.set(entity.icon, img)
      }
      if (!img.complete) {
        return
      }

      // Slight upward nudge keeps the icon visually aligned with label glyphs.
      const y = yScale.getPixelForTick(tickIndex) - iconSize / 2 - 1
      const label = getEntityLabel(entity)
      const labelWidth = ctx.measureText(label).width
      const x =
        yScale.right - tickPadding * 1.6 - labelWidth - iconGap - iconSize

      ctx.drawImage(img, x, y, iconSize, iconSize)
    })
  },
}

const firstEntryIconsPlugin: Plugin<"scatter"> = {
  id: "firstEntryIcons",
  afterDatasetsDraw: (chart) => {
    const ctx = chart.ctx
    const chartArea = chart.chartArea
    if (!ctx || !chartArea) {
      return
    }

    const orderedEntities = getOrderedEntities()
    const iconSize = 14
    const iconGap = 20

    chart.data.datasets.forEach((_, datasetIndex) => {
      const entity = orderedEntities[datasetIndex]
      if (!entity?.icon) {
        return
      }

      const meta = chart.getDatasetMeta(datasetIndex)
      const firstPoint = meta?.data?.[0] as
        | {
            getProps: (
              keys: string[],
              final: boolean,
            ) => { x?: number; y?: number }
          }
        | undefined
      if (!firstPoint) {
        return
      }

      const { x, y } = firstPoint.getProps(["x", "y"], true)
      if (
        x === undefined ||
        y === undefined ||
        !Number.isFinite(x) ||
        !Number.isFinite(y)
      ) {
        return
      }

      let img = iconCache.get(entity.icon)
      if (!img) {
        img = new Image()
        img.src = entity.icon
        img.onload = () => {
          refreshChartWhenVisible()
        }
        iconCache.set(entity.icon, img)
      }
      if (!img.complete) {
        return
      }

      const drawX = Math.max(chartArea.left + 2, x - iconSize - iconGap)
      const drawY = y - iconSize / 2
      ctx.drawImage(img, drawX, drawY, iconSize, iconSize)
    })
  },
}

chartPlugins.push(yTickIconsPlugin)
chartPlugins.push(firstEntryIconsPlugin)

onMounted(async () => {
  await loadData()
})

function normalizeArray(arr: number[], from = 0, to = 1): number[] {
  const min = Math.min(...arr)
  const max = Math.max(...arr)
  if (max === min) {
    return arr.map(() => (from + to) / 2)
  }
  return arr.map((value) => ((value - min) / (max - min)) * (to - from) + from)
}

function refColors(): string[] {
  const green = ["#b3d4c9", "#4dbd98", "#1f805f"]
  const orange = ["#e57126", "#f57d49", "#ca5202"]
  const blue = ["#3d9bcc", "#6f89de", "#688ea2"]
  const yellow = ["#e7a824", "#f0c66e", "#ad7602"]
  const colors = []
  for (let i = 0; i < blue.length; i++) {
    colors.push(blue[i])
    colors.push(orange[i])
    colors.push(green[i])
    colors.push(yellow[i])
  }
  return colors
}

interface EntityWithTransfers extends Entity {
  transfers: Transfer[]
}

async function loadData() {
  const currentYear = new Date().getFullYear()
  const entitiesById = props.entities.reduce<
    Record<string, EntityWithTransfers>
  >((acc, entity) => {
    acc[entity.id] = { ...entity, transfers: [] }
    return acc
  }, {})
  props.transfers.map((transfer) => {
    if (entitiesById[transfer.recipient_id].transfers === undefined) {
      entitiesById[transfer.recipient_id].transfers = [transfer]
    } else {
      entitiesById[transfer.recipient_id].transfers.push(transfer)
    }
  })
  chartData.value = {
    labels: getOrderedEntities().map((_, index) => index),
    datasets: getOrderedEntities().map((entity, index) => {
      const sortedTransfers = [...entitiesById[entity.id].transfers].sort(
        (a, b) => {
          const aDate = a.date_clc.dateObj?.getTime() || 0
          const bDate = b.date_clc.dateObj?.getTime() || 0
          return aDate - bDate
        },
      )
      const lastTransfer = sortedTransfers[sortedTransfers.length - 1]
      const lastTransferYear = lastTransfer?.date_clc.dateObj?.getFullYear()
      const shouldDrawGapToNextYear =
        lastTransferYear !== undefined && lastTransferYear === currentYear - 1

      const dataPoints: Array<{
        x: Date | undefined
        y: number
        amount: number
        isLastRealPoint?: boolean
        isYearExtension?: boolean
        isGapStart?: boolean
        isGapToNextYear?: boolean
      }> = sortedTransfers.map((transfer, transferIndex) => ({
        x: transfer.date_clc.dateObj,
        y: index,
        amount: transfer.amounts_clc?.[selectedCurrency.value.id] || 0,
        isLastRealPoint: transferIndex === sortedTransfers.length - 1,
      }))

      if (lastTransferYear !== undefined && lastTransfer) {
        const endOfLastPaymentYear = new Date(lastTransferYear, 11, 31)
        const lastDateMs = lastTransfer.date_clc.dateObj?.getTime() || 0

        if (shouldDrawGapToNextYear) {
          if (endOfLastPaymentYear.getTime() > lastDateMs) {
            dataPoints.push({
              x: endOfLastPaymentYear,
              y: index,
              amount:
                lastTransfer.amounts_clc?.[selectedCurrency.value.id] || 0,
              isYearExtension: true,
              isGapStart: true,
            })
          }

          const endOfCurrentYear = new Date(currentYear, 11, 31)
          if (endOfCurrentYear.getTime() > endOfLastPaymentYear.getTime()) {
            dataPoints.push({
              x: endOfCurrentYear,
              y: index,
              amount:
                lastTransfer.amounts_clc?.[selectedCurrency.value.id] || 0,
              isYearExtension: true,
              isGapToNextYear: true,
            })
          }
        } else if (endOfLastPaymentYear.getTime() > lastDateMs) {
          dataPoints.push({
            x: endOfLastPaymentYear,
            y: index,
            amount: lastTransfer.amounts_clc?.[selectedCurrency.value.id] || 0,
            isYearExtension: true,
          })
        }
      }

      const normalizedRadii = normalizeArray(
        sortedTransfers.map(
          (transfer) => transfer.amounts_clc?.[selectedCurrency.value.id] || 0,
        ),
        3,
        8,
      )

      return {
        type: "scatter",
        label: entity.short_name || entity.name,
        showLine: true,
        segment: {
          borderDash: (ctx: any) => {
            const p0 = ctx.p0.raw as {
              isLastRealPoint?: boolean
              isGapStart?: boolean
            }
            const p1 = ctx.p1.raw as {
              isYearExtension?: boolean
              isGapToNextYear?: boolean
            }
            if (
              (p0?.isGapStart || p0?.isLastRealPoint) &&
              p1?.isYearExtension &&
              p1?.isGapToNextYear
            ) {
              return [6, 6]
            }
            return undefined
          },
        },
        data: dataPoints,
        pointRadius: (ctx: any) => {
          const raw = ctx.raw as { isYearExtension?: boolean }
          if (raw?.isYearExtension) {
            return 0
          }
          return normalizedRadii[ctx.dataIndex] ?? 3
        },
        pointBackgroundColor: refColors()[index % refColors().length],
        pointBorderColor: "white",
        borderColor: refColors()[index % refColors().length],
      }
    }),
  }

  const maxLabelLength = getOrderedEntities().reduce(
    (max, entity) => Math.max(max, getEntityLabel(entity).length),
    0,
  )
  chartOptions.value = {
    scales: {
      x: {
        type: "time",
        time: {
          unit: "year",
        },
        title: {
          display: true,
        },
        min: (
          Math.min(
            ...props.transfers.map(
              (transfer) =>
                transfer.date_clc.dateObj?.getFullYear() ||
                new Date().getFullYear(),
            ),
          ) - 1
        ).toString(),
        max: (
          Math.max(
            ...props.transfers.map(
              (transfer) =>
                transfer.date_clc.dateObj?.getFullYear() ||
                new Date().getFullYear(),
            ),
          ) + 1
        ).toString(),
      },
      y: {
        min: -1,
        max: props.entities.length,
        ticks: {
          stepSize: 1,
          padding: 24,
          callback: (value: string | number) => {
            const entity = getOrderedEntities()[Number(value)]
            return entity ? getEntityLabel(entity) : ""
          },
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: "nearest",
        intersect: false,
        callbacks: {
          label: (context: TooltipItem<"scatter">) => {
            const raw = context.raw as { amount?: number }
            const amount = raw.amount || 0
            return `${context.dataset.label}: ${amount.toLocaleString()} ${selectedCurrency.value.id}`
          },
        },
      },
    },
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
  }
  loading.value = false

  // Force one post-render pass once the canvas becomes visible.
  void nextTick(() => {
    refreshChartWhenVisible()
  })
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
  alert("Not implemented yet!")
}
</script>

<template>
  <div class="chart-wrapper">
    <div class="chart-container" :style="chartContainerStyle">
      <Loader v-if="loading" width="200px" />
      <Chart
        v-show="!loading"
        ref="chart"
        class="chart"
        type="scatter"
        :data="chartData"
        :options="chartOptions"
        :plugins="chartPlugins"
      />
    </div>
    <div class="chart-header">
      <div class="chart-legend" aria-label="Timeline legend">
        <div class="chart-legend-item">
          <span class="chart-legend-line chart-legend-line-solid" />
          <span>Infrastructure supported</span>
        </div>
        <div class="chart-legend-item">
          <span class="chart-legend-line chart-legend-line-dotted" />
          <span>Support not yet confirmed</span>
        </div>
        <div class="chart-legend-item">
          <span class="chart-legend-dot" />
          <span>Support date</span>
        </div>
      </div>
      <h2 class="chart-title">
        {{ chartTitle }}
      </h2>
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  min-width: 300px;
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
  margin-top: 2rem;
}

.chart-legend {
  margin-top: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem 1.25rem;
}

.chart-legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.chart-legend-line {
  width: 2.25rem;
  border-top: 3px solid #2f3e4d;
}

.chart-legend-line-dotted {
  border-top-style: dashed;
}

.chart-legend-dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
  background: #2f3e4d;
  display: inline-block;
}

.chart-container {
  display: flex;
  justify-content: center;
}

.chart {
  position: relative;
  width: 100%;
}

.chart-description {
  margin-left: auto;
  margin-right: auto;
  width: fit-content;
}
</style>
