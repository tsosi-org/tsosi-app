<script setup lang="ts">
import {
  getEntityDetails,
  getEntitySummary,
  type EntityDetails,
  type DeepReadonly,
} from "@/singletons/ref-data"
import { useRoute, useRouter } from "vue-router"
import { ref, type Ref, onBeforeMount, watch } from "vue"
import { changeTitle } from "@/utils/dom-utils"
import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import EntityData from "@/components/EntityData.vue"

const route = useRoute()
const router = useRouter()

const entity: Ref<DeepReadonly<EntityDetails> | null> = ref(null)

onBeforeMount(async () => {
  const result = await getEntitySummary(route.params.id as string)
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  entity.value = await getEntityDetails(route.params.id as string)
})

async function onEntityChange() {
  if (!entity.value) {
    return
  }
  changeTitle(entity.value.name)
}

watch(entity, onEntityChange)
</script>

<template>
  <Loader v-show="!entity" width="150px"></Loader>
  <div class="container" v-if="entity">
    <div class="regular-content">
      <EntityMeta :entity="entity as EntityDetails" />
      <EntityData :entity="entity as EntityDetails" />
    </div>
  </div>
</template>
