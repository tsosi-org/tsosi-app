<script setup lang="ts">
import {
  Chart,
  registerables,
  type ChartData,
  type ChartOptions,
  type Plugin,
} from "chart.js"
import { TreemapController, TreemapElement } from "chartjs-chart-treemap"
import { onBeforeUnmount, onMounted, ref } from "vue"

// Register Chart.js components
Chart.register(...registerables)
Chart.register(TreemapController, TreemapElement)

export interface TreemapChartProps {
  data: ChartData
  options: ChartOptions
  plugins?: Plugin[]
}

const props = defineProps<TreemapChartProps>()

const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

onMounted(() => {
  if (chartCanvas.value) {
    chartInstance = new Chart(chartCanvas.value, {
      type: "treemap",
      data: props.data,
      options: props.options,
      plugins: props.plugins,
    })
  }
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

// Expose update method if you need to manually update
defineExpose({
  update: () => {
    if (chartInstance) {
      chartInstance.update()
    }
  },
})
</script>

<template>
  <div>
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>
