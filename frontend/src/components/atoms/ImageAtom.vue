<script setup lang="ts">
import { ref, onMounted, useTemplateRef, computed } from "vue"

const props = defineProps<{
  src?: string
  width?: string
  height?: string
  containerPadding?: string
  center?: boolean
}>()

const sizeDefault = "50px"
const loading = ref(true)
const imgElement = useTemplateRef("img")
const isSvg = computed(() => props.src?.endsWith(".svg"))

const imgWidth = computed(() => props.width ?? sizeDefault)
const imgHeight = computed(() => props.height ?? imgWidth.value)
const imgContainerPadding = computed(() => props.containerPadding ?? "5px")
const iconFontSize = computed(
  () =>
    `min(calc(${imgWidth.value} - 2 * ${imgContainerPadding.value}) / 2, 100px)`,
)

onMounted(() => {
  imgElement.value?.addEventListener("load", () => {
    loading.value = false
  })
})
</script>

<template>
  <figure class="img-container" :class="{ center: props.center, svg: isSvg }">
    <font-awesome-icon v-show="loading" class="icon" :icon="['fas', 'image']" />
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
  width: v-bind(imgWidth);
  height: v-bind(imgHeight);
  padding: v-bind(imgContainerPadding);
  text-align: center;
  flex-shrink: 0;

  &.center {
    display: flex;
    place-items: center;
    place-content: center;
  }

  &.svg .content {
    width: 100%;
    height: 100%;
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
