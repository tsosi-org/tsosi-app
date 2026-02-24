<script setup lang="ts">
import DynamicDialog from "primevue/dynamicdialog"
import { useDialog } from "primevue/usedialog"
import { onMounted, ref, watch } from "vue"
import { RouterView, useRoute } from "vue-router"

import SiteInConstructionAtom from "./components/atoms/SiteInConstructionAtom.vue"
import { targetElement } from "./utils/dom-utils"

import Loader from "@/components/atoms/LoaderAtom.vue"
import ContactComponent from "@/components/ContactComponent.vue"
import FooterLayout from "@/layouts/FooterLayout.vue"
import HeaderLayout from "@/layouts/HeaderLayout.vue"
import { refDataPromise } from "@/singletons/ref-data"

const loading = ref(true)
const route = useRoute()
const dialog = useDialog()

onMounted(async () => {
  await onInit()
  setTimeout(() => scrollToHash(true), scrollTimeout)
  if (import.meta.env.VITE_WELCOME_POPUP === "true") {
    setTimeout(
      () =>
        dialog.open(SiteInConstructionAtom, {
          props: {
            modal: true,
            baseZIndex: 10000,
          },
        }),
      scrollTimeout + 500,
    )
  }
})

watch(
  () => route.hash,
  () => scrollToHash(true),
)

const scrollTimeout = 300
async function onInit() {
  const loaded = await refDataPromise
  if (loaded) {
    loading.value = false
  }
}

function scrollToHash(retry: boolean) {
  const hash = window.location.hash
  if (hash) {
    const element = document.querySelector(hash)
    if (element) {
      targetElement(element)
      element.scrollIntoView(true)
    } else if (retry) {
      setTimeout(() => scrollToHash, scrollTimeout, false)
    }
  }
}
</script>

<template>
  <DynamicDialog />
  <Loader v-show="loading" width="200px"></Loader>
  <template v-if="!loading">
    <HeaderLayout />
    <main id="main" class="page-content">
      <RouterView v-if="!loading" :key="$route.path" />
      <ContactComponent />
    </main>
    <FooterLayout />
  </template>
</template>
