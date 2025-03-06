<script setup lang="ts">
import Popover from "primevue/popover"
import { onMounted, useTemplateRef } from "vue"
import { addClickEventListener } from "@/utils/dom-utils"

const props = defineProps<{ content?: string }>()
const popup = useTemplateRef("popup")
const iconButton = useTemplateRef("icon-button")
let hidePopup = true

onMounted(() => attachEvents())

function attachEvents() {
  if (!iconButton.value) {
    return
  }
  addClickEventListener(iconButton.value, toggle)
  iconButton.value.addEventListener("mouseenter", show)
  iconButton.value.addEventListener("mouseleave", triggerHide)
}

function toggle(event: Event) {
  popup.value?.toggle(event)
}

function show(event: Event) {
  popup.value?.show(event)
}

function hide(_: Event) {
  if (hidePopup) {
    popup.value?.hide()
  }
}

function triggerHide(event: Event) {
  setTimeout(() => hide(event), 200)
}

function popupLeave(event: Event) {
  hidePopup = true
  setTimeout(() => hide(event), 200)
}
</script>

<template>
  <div class="info-button" ref="icon-button" tabindex="0">
    <font-awesome-icon
      icon="circle-question"
      class="info-icon"
    ></font-awesome-icon>
    <Popover
      ref="popup"
      :baseZIndex="1000"
      class="popup-wrapper"
      @mouseenter="hidePopup = false"
      @mouseleave="popupLeave"
    >
      <div class="info-popup">
        <slot></slot>
        <div v-if="props.content" v-html="props.content"></div>
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
  text-align: initial;
  color: initial;
  font-weight: initial;
}
</style>
