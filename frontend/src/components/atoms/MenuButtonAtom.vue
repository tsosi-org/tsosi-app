<script setup lang="ts">
import Menu from "primevue/menu"
import ButtonAtom, { type ButtonProps } from "./ButtonAtom.vue"
import { useTemplateRef } from "vue"

/**
 * Copy-pasted from primevue/menuitem bc the type is not exported..
 */
export interface MenuItem {
  label?: string | ((...args: any) => string) | undefined
  icon?: string | undefined
  command?: (event: {
    originalEvent: Event
    item: MenuItem
    [key: string]: any
  }) => void
  url?: string | undefined
  items?: MenuItem[] | undefined
  disabled?: boolean | ((...args: any) => boolean) | undefined
  visible?: boolean | ((...args: any) => boolean) | undefined
  target?: string | undefined
  separator?: boolean | undefined
  style?: any
  class?: any
  key?: string | undefined
  [key: string]: any
}

export interface MenuButtonAtomProps {
  button: ButtonProps
  id: string
  items: MenuItem[]
}

const props = defineProps<MenuButtonAtomProps>()
const menu = useTemplateRef("menu")

function toggleMenu(event: Event) {
  menu.value!.toggle(event)
  event.stopPropagation()
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
