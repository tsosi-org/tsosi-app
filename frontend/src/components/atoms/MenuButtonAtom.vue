<script setup lang="ts">
import { type MenuItem } from "primevue/menuitem"
import Menu from "primevue/menu"
import ButtonAtom, { type ButtonProps } from "./ButtonAtom.vue"
import { useTemplateRef } from "vue"

export interface MenuButtonAtomProps {
  button: ButtonProps
  id: string
  items: MenuItem[]
}

const props = defineProps<MenuButtonAtomProps>()
const menu = useTemplateRef("menu")

function toggleMenu(event: Event) {
  menu.value!.toggle(event)
}
</script>

<template>
  <ButtonAtom
    v-bind="props.button"
    @click="toggleMenu"
    aria-haspopup="true"
    :aria-controls="props.id"
  />
  <Menu ref="menu" :id="props.id" :model="props.items" :popup="true">
    <template #itemicon="{ item }">
      <font-awesome-icon v-if="item.icon" :icon="item.icon" />
    </template>
  </Menu>
</template>
