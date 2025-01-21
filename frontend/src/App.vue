<script setup lang="ts">
import { ref, onMounted } from "vue"
import { RouterView } from "vue-router"
import Header from "./layouts/HeaderLayout.vue"
import Loader from "./components/atoms/LoaderAtom.vue"
import { refDataPromise } from "./singletons/ref-data"

const loading = ref(true)

async function onInit() {
  const loaded = await refDataPromise
  if (loaded) {
    loading.value = false
  }
}

onMounted(async () => {
  await onInit()
})
</script>

<template>
  <Loader v-show="loading" width="200px"></Loader>
  <template v-if="!loading">
    <Header />
    <main class="page-content" :key="$route.path">
      <RouterView v-if="!loading" />
    </main>
  </template>
</template>
