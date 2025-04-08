<script setup lang="ts">
import { ref, watch, onMounted, useTemplateRef, onBeforeMount } from "vue"

const props = defineProps<{
  src?: string
  width?: string
  height?: string
  containerPadding?: string
  center?: boolean
}>()

const loading = ref(true)
const imgElement = useTemplateRef("img")
const width = ref("")
const height = ref("")
const containerPadding = ref("")
const iconFontSize = ref("")

const sizeDefault = "50px"

onBeforeMount(() => updateImageDimensions())
watch(() => props.width && props.height, updateImageDimensions)
onMounted(() => {
  imgElement.value?.addEventListener("load", () => {
    loading.value = false
  })
})

function updateImageDimensions() {
  width.value = props.width ?? sizeDefault
  height.value = props.height ?? width.value
  containerPadding.value = props.containerPadding ?? "5px"
  iconFontSize.value = `min(calc(${width.value} - 2 * ${containerPadding.value}) / 2, 100px)`
}
</script>

<template>
  <figure class="img-container" :class="{ center: props.center }">
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
  width: v-bind(width);
  height: v-bind(height);
  padding: v-bind(containerPadding);
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
