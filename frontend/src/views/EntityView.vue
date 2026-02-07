<script setup lang="ts">
import {
  onBeforeMount,
  onBeforeUnmount,
  shallowRef,
  watch,
  type ShallowRef,
} from "vue"
import { useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import EntityData from "@/components/EntityData.vue"
import EntityMeta from "@/components/EntityMeta.vue"
import {
  getEntityDetails,
  getEntitySummary,
  resolveEntityRoute,
  type DeepReadonly,
  type EntityDetails,
} from "@/singletons/ref-data"
import {
  changeMetaDescripion,
  changeMetaTitle,
  changeMetaUrl,
} from "@/utils/dom-utils"


const entity: ShallowRef<DeepReadonly<EntityDetails> | null> = shallowRef(null)

watch(entity, onEntityChange)

onBeforeMount(async () => {
  const route = useRoute()
  const router = useRouter()
  const entityId = resolveEntityRoute(route.params.id as string)

  const result = entityId ? getEntitySummary(entityId) : undefined
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  entity.value = await getEntityDetails(result.id)
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

onBeforeUnmount(() => {
  entity.value = null
})
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
