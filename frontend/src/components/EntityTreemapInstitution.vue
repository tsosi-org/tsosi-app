<script setup lang="ts">
import Loader from "@/components/atoms/LoaderAtom.vue"
import TreemapChart from "@/components/atoms/TreemapChartAtom.vue"
import { selectedCurrency } from "@/singletons/currencyStore"
import { type Entity, type Transfer } from "@/singletons/ref-data"
import type { ChartOptions, Plugin } from "chart.js"
import Color from "colorjs.io"
import { onMounted, ref, useTemplateRef, type Ref } from "vue"

const props = defineProps<{
  role: "emitter" | "recipient"
  entity: Entity
  entities: Entity[]
  transfers: Transfer[] | null
  disableExport?: boolean
}>()
const chartData: Ref<any | undefined> = ref()
const chartOptions: Ref<ChartOptions> = ref({})
const amounts: Ref<Record<string, Record<string, number>> | null> = ref(null)
const loading = ref(true)
const chartPlugins: Plugin[] = []
// const chartTitle = `Distribution of supports by infrastructure - ${props.entity.short_name || props.entity.name}`
const chartTitle = `Distribution of supports by infrastructure`
const chartComponent = useTemplateRef("chart")
const iconCache = new Map<string, HTMLImageElement>()
const TILE_ICON_SIZE = 18
const TILE_ICON_MARGIN = 10
const TILE_HOVER_FIXED_WIDTH = 240
const TILE_HOVER_FIXED_HEIGHT = 140
const TILE_HOVER_MAX_AREA = 35000
const TILE_LABEL_MAX_AREA = 10000
let hoverAnimationProgress = 0
let hoverAnimationTarget = 0
let hoverAnimationFrame: number | null = null
let hoverAnimationChart: any = null
let hoverAnimationActiveKey: string | null = null

function scheduleHoverAnimation(chart: any) {
  hoverAnimationChart = chart
  if (hoverAnimationFrame != null) {
    return
  }

  const step = () => {
    const delta = hoverAnimationTarget - hoverAnimationProgress
    if (Math.abs(delta) < 0.01) {
      hoverAnimationProgress = hoverAnimationTarget
      hoverAnimationFrame = null
      if (hoverAnimationProgress > 0 && hoverAnimationChart?.draw) {
        hoverAnimationChart.draw()
      }
      return
    }

    hoverAnimationProgress += delta * 0.18
    hoverAnimationChart?.draw?.()
    hoverAnimationFrame = window.requestAnimationFrame(step)
  }

  hoverAnimationFrame = window.requestAnimationFrame(step)
}

function getEntityById(entityId: string): Entity | undefined {
  return props.entities.find((entity) => entity.id === entityId)
}

const treemapIconsPlugin: Plugin = {
  id: "treemapIcons",
  afterDatasetsDraw: (chart) => {
    const ctx = chart.ctx
    if (!ctx) {
      return
    }

    const meta = chart.getDatasetMeta(0)
    if (!meta?.data?.length) {
      return
    }

    meta.data.forEach((element: any) => {
      const raw = element?.$context?.raw
      const data = raw?._data
      if (!data?.id) {
        return
      }

      const entity = getEntityById(data.id)
      if (!entity?.icon) {
        return
      }

      let img = iconCache.get(entity.icon)
      if (!img) {
        img = new Image()
        img.src = entity.icon
        img.onload = () => {
          if (!chart.ctx || !chart.canvas || !chart.attached) {
            return
          }
          chart.draw()
        }
        iconCache.set(entity.icon, img)
      }
      if (!img.complete || !img.naturalWidth || !img.naturalHeight) {
        return
      }

      const { x, y, width, height } = element.getProps(
        ["x", "y", "width", "height"],
        true,
      )
      if (
        !width ||
        !height ||
        width < TILE_ICON_SIZE * 2 ||
        height < TILE_ICON_SIZE
      ) {
        return
      }

      const scale = Math.min(
        TILE_ICON_SIZE / img.naturalWidth,
        TILE_ICON_SIZE / img.naturalHeight,
      )
      const drawWidth = img.naturalWidth * scale
      const drawHeight = img.naturalHeight * scale
      const left = x
      const top = y
      const drawX = left + width - TILE_ICON_MARGIN - drawWidth
      const drawY = top + TILE_ICON_MARGIN

      ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight)
    })
  },
}

const treemapHoverGrowPlugin: Plugin = {
  id: "treemapHoverGrow",
  afterDatasetsDraw: (chart) => {
    const ctx = chart.ctx
    if (!ctx) {
      return
    }

    const activeElements = chart.getActiveElements()
    const activeElement = activeElements.find(({ element }: any) => {
      const { width, height } = element.getProps(["width", "height"], true)
      return !!width && !!height && width * height <= TILE_HOVER_MAX_AREA
    })

    const activeKey = activeElement
      ? String((activeElement.element as any)?.$context?.raw?._data?.id || "")
      : null

    if (activeKey !== hoverAnimationActiveKey) {
      hoverAnimationActiveKey = activeKey
      hoverAnimationProgress = 0
    }

    hoverAnimationTarget = activeElement ? 1 : 0
    scheduleHoverAnimation(chart)

    if (!activeElement && hoverAnimationProgress <= 0.01) {
      return
    }

    const element = activeElement?.element as any
    if (!element) {
      return
    }

    const { x, y, width, height } = element.getProps(
      ["x", "y", "width", "height"],
      true,
    )
    if (!width || !height) {
      return
    }

    const raw = element?.$context?.raw
    const data = raw?._data
    if (!data?.id) {
      return
    }

    const entity = getEntityById(data.id)
    if (!entity) {
      return
    }

    const value = raw?.v
    const since = amounts.value?.[data.id]?.since || "N/A"
    const hoverWidth = Math.max(width, TILE_HOVER_FIXED_WIDTH)
    const hoverHeight = Math.max(height, TILE_HOVER_FIXED_HEIGHT)
    const hoverX = x + width - hoverWidth
    const hoverY = y + height - hoverHeight

    const fillColor =
      (element?.options as { backgroundColor?: string })?.backgroundColor ||
      "transparent"
    const borderColor =
      (element?.options as { borderColor?: string })?.borderColor || "white"
    const borderWidth =
      (element?.options as { borderWidth?: number })?.borderWidth || 1

    const easedProgress = Math.min(Math.max(hoverAnimationProgress, 0), 1)
    const currentWidth = width + (hoverWidth - width) * easedProgress
    const currentHeight = height + (hoverHeight - height) * easedProgress
    const currentX = x + width - currentWidth
    const currentY = y + height - currentHeight

    ctx.save()
    ctx.shadowColor = "rgba(0, 0, 0, 0.18)"
    ctx.shadowBlur = 10

    ctx.beginPath()
    ctx.fillStyle = fillColor
    ctx.fillRect(currentX, currentY, currentWidth, currentHeight)

    ctx.lineWidth = borderWidth
    ctx.strokeStyle = borderColor
    ctx.strokeRect(currentX, currentY, currentWidth, currentHeight)

    ctx.fillStyle = "rgb(44, 62, 80)"
    ctx.textBaseline = "top"

    ctx.font = "bold 20px sans-serif"
    ctx.fillText(entity.short_name || entity.name, currentX + 10, currentY + 10)

    ctx.font = "12px sans-serif"
    ctx.fillText(
      `${Number(value || 0).toLocaleString()} ${selectedCurrency.value.id} - since ${since}`,
      currentX + 10,
      currentY + 30,
    )

    if (entity.icon) {
      let img = iconCache.get(entity.icon)
      if (!img) {
        img = new Image()
        img.src = entity.icon
        iconCache.set(entity.icon, img)
      }
      if (img.complete && img.naturalWidth && img.naturalHeight) {
        const iconScale = Math.min(
          TILE_ICON_SIZE / img.naturalWidth,
          TILE_ICON_SIZE / img.naturalHeight,
        )
        const drawWidth = img.naturalWidth * iconScale
        const drawHeight = img.naturalHeight * iconScale
        ctx.drawImage(
          img,
          currentX + currentWidth - TILE_ICON_MARGIN - drawWidth,
          currentY + TILE_ICON_MARGIN,
          drawWidth,
          drawHeight,
        )
      }
    }

    ctx.restore()
  },
}

chartPlugins.push(treemapIconsPlugin)
chartPlugins.push(treemapHoverGrowPlugin)

onMounted(async () => {
  await loadData()
  updateChart()
  loading.value = false
})

async function loadData() {
  if (!props.transfers) {
    amounts.value = {}
    return
  }

  amounts.value = props.transfers
    .filter(
      (transfer) =>
        transfer.amounts_clc && transfer.recipient_id != props.entity.id,
    )
    .reduce((acc: any, transfer) => {
      const entityId =
        props.role == "emitter" ? transfer.recipient_id : transfer.emitter_id
      if (acc[entityId] === undefined) {
        acc[entityId] = { ...transfer.amounts_clc }
      } else {
        for (const currency in transfer.amounts_clc) {
          if (acc[entityId][currency]) {
            acc[entityId][currency] += transfer.amounts_clc[currency]
          } else {
            delete acc[entityId][currency]
          }
        }
      }
      if (transfer.date_clc.dateObj) {
        acc[entityId]["since"] = Math.min(
          acc[entityId]["since"] || new Date().getFullYear(),
          transfer.date_clc.dateObj.getFullYear(),
        )
      }
      return acc
    }, {})
}

function updateChart() {
  const currentAmounts = amounts.value ?? {}

  chartData.value = {
    datasets: [
      {
        tree: props.entities
          .map((entity) => ({
            value:
              (currentAmounts[entity.id] &&
                currentAmounts[entity.id][selectedCurrency.value.id]) ||
              0,
            label: entity.short_name || entity.name,
            id: entity.id,
          }))
          .sort((a, b) => b.value - a.value)
          .map((item) => {
            return item
          }),
        key: "value",
        backgroundColor: (ctx: any) => {
          const ref = refColors()
          if (ctx.type !== "data") {
            return "transparent"
          }
          const value = ctx.raw.v
          const color = refColors()[ctx.dataIndex % ref.length]
          if (ctx.active) {
            return Color.darken(color, 0.1).toString()
          }
          return color
        },
        borderWidth: 1,
        borderColor: "white",
        spacing: 0,
        labels: {
          display: true,
          overflow: "fit",
          padding: 10,
          align: "left",
          position: "top",
          color: ["rgb(44, 62, 80)", "rgb(44, 62, 80)"],
          font: [{ size: 20, weight: "bold" }, { size: 12 }],
          formatter(ctx: any) {
            if (ctx.type !== "data") {
              return
            }
            if (ctx.raw.w * ctx.raw.h <= TILE_LABEL_MAX_AREA) {
              return ""
            }
            return [
              `${ctx.raw._data.label}`,
              `${ctx.raw.v.toLocaleString()} ${selectedCurrency.value.id} - since ${currentAmounts[ctx.raw._data.id]?.since || "N/A"}`,
            ]
          },
        },
      },
    ],
  }
  chartOptions.value = {
    responsive: true,
    maintainAspectRatio: true,
    animation: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        enabled: false,
      },
    },
  }
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

function getFileName(): string {
  const baseName = props.entity.name.replace(/\s+/g, "_")
  const chartTitleClean = chartTitle.replace(/\s+/g, "_")
  return `TSOSI_${baseName}_${chartTitleClean}`
}

async function downloadPNG() {
  alert("Not implemented yet!")
}

async function downloadData(format: "json" | "csv") {
  alert("Not implemented yet!")
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
</script>

<template>
  <div class="chart-wrapper">
    <div class="chart-container">
      <Loader v-if="loading" width="200px" />
      <TreemapChart
        v-else
        ref="chart"
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
  margin-bottom: 100px;

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

.chart-description {
  margin-left: auto;
  margin-right: auto;
  width: fit-content;
}
</style>
