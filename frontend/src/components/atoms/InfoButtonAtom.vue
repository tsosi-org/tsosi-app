<script setup lang="ts">
import Popover from "primevue/popover"
import { onMounted, useTemplateRef } from "vue"
import { addClickEventListener } from "@/utils/dom-utils"

const popup = useTemplateRef("popup")
const iconButton = useTemplateRef("icon-button")

onMounted(() => attachEvents())

function attachEvents() {
  if (!iconButton.value) {
    return
  }
  addClickEventListener(iconButton.value, toggle)
  iconButton.value.addEventListener("mouseenter", show)
  iconButton.value.addEventListener("mouseleave", hide)
}

function toggle(event: Event) {
  popup.value?.toggle(event)
}

function show(event: Event) {
  popup.value?.show(event)
}

function hide(_: Event) {
  popup.value?.hide()
}
</script>

<template>
  <div class="info-button" ref="icon-button" tabindex="0">
    <font-awesome-icon
      icon="circle-question"
      class="info-icon"
    ></font-awesome-icon>
    <Popover ref="popup" :baseZIndex="1000" class="popup-wrapper">
      <div class="info-popup">
        <slot> My info content </slot>
      </div>
    </Popover>
  </div>
</template>

<style scoped>
.info-button {
  display: inline-block;
  position: relative;
  padding: 2px;
  border-radius: 2px;
}

.info-button:focus,
.info-button:focus-visible {
  outline: 1px solid var(--p-primary-color);
  outline-offset: -1px;
}

.popup-wrapper::before {
  all: unset;
}

.info-popup {
  max-width: min(80vw, 400px);
}
</style>
