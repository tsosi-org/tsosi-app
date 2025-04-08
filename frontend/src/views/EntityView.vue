<script setup lang="ts">
import {
  getEntityDetails,
  getEntitySummary,
  type EntityDetails,
  type DeepReadonly,
} from "@/singletons/ref-data"
import { useRoute, useRouter } from "vue-router"
import { ref, type Ref, onBeforeMount, watch } from "vue"
import {
  changeMetaTitle,
  changeMetaDescripion,
  changeMetaUrl,
} from "@/utils/dom-utils"
import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import EntityData from "@/components/EntityData.vue"

const route = useRoute()
const router = useRouter()

const entity: Ref<DeepReadonly<EntityDetails> | null> = ref(null)

watch(entity, onEntityChange)

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
  changeMetaTitle(entity.value.name)
  const desc = entity.value.is_recipient
    ? `Explore the funding made to sustain ${entity.value.name}`
    : `Explore the funding performed by ${entity.value.name}`
  changeMetaDescripion(desc)
  changeMetaUrl(true)
}
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
