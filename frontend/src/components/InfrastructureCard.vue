<script lang="ts" setup>
import { type Entity } from "@/singletons/ref-data"
import Card from "primevue/card"
import ImageAtom from "./atoms/ImageAtom.vue"
import { getEntityUrl } from "@/utils/url-utils"

const props = defineProps<{ entity: Entity }>()
</script>

<template>
  <Card style="position: relative; width: 18rem">
    <template #header>
      <div style="display: flex; place-content: center">
        <ImageAtom
          :src="props.entity.logo"
          width="15rem"
          :center="true"
        ></ImageAtom>
      </div>
    </template>
    <template #title>
      <div style="text-align: center">
        <RouterLink :to="getEntityUrl(props.entity.id)">
          {{ props.entity.name }}
        </RouterLink>
      </div>
    </template>
    <template #content> </template>
  </Card>
</template>

<style scoped></style>
