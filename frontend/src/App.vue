<script setup lang="ts">
import { ref, onMounted, watch } from "vue"
import { RouterView, useRoute } from "vue-router"
import HeaderLayout from "@/layouts/HeaderLayout.vue"
import Loader from "@/components/atoms/LoaderAtom.vue"
import { refDataPromise } from "@/singletons/ref-data"
import FooterLayout from "@/layouts/FooterLayout.vue"

const loading = ref(true)
const route = useRoute()

onMounted(async () => {
  await onInit()
  setTimeout(() => scrollToHash(true), scrollTimeout)
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
      element.scrollIntoView()
    } else if (retry) {
      setTimeout(() => scrollToHash, scrollTimeout, false)
    }
  }
}
</script>

<template>
  <Loader v-show="loading" width="200px"></Loader>
  <template v-if="!loading">
    <HeaderLayout />
    <main id="main" class="page-content" :key="$route.path">
      <RouterView v-if="!loading" />
    </main>
    <FooterLayout />
  </template>
</template>
