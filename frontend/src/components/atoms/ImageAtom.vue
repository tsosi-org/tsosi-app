<script setup lang="ts">
import { ref, onMounted, useTemplateRef } from "vue"

const props = defineProps<{
  src?: string
  width?: string
  height?: string
  containerPadding?: string
  center?: boolean
}>()

const loading = ref(true)
const imgElement = useTemplateRef("img")

const sizeDefault = "50px"
const width = props.width ?? sizeDefault
const height = props.height ?? width
const containerPadding = props.containerPadding ?? "5px"
const iconFontSize = `min(calc(${width} - 2 * ${containerPadding}) / 2, 100px)`

onMounted(() => {
  imgElement.value?.addEventListener("load", () => {
    loading.value = false
  })
})
</script>

<template>
  <figure
    class="img-container"
    :class="{ center: props.center }"
    :style="{ width: width, padding: containerPadding }"
  >
    <font-awesome-icon v-show="loading" class="icon" icon="image" />
    <img
      v-if="props.src"
      v-show="!loading"
      class="content"
      :src="props.src"
      ref="img"
    />
  </figure>
</template>

<style scoped>
.img-container {
  font-size: 1rem;
  width: v-bind("width");
  height: v-bind("height");
  padding: v-bind("containerPadding");
  text-align: center;
  flex-shrink: 0;

  &.center {
    display: flex;
    place-items: center;
    place-content: center;
  }
}

.icon {
  font-size: v-bind("iconFontSize");
  color: var(--p-primary-800);
}

.content {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
  border-radius: 4px;
}
</style>
