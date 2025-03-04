<script setup lang="ts">
import { ref, watch } from "vue"
import { RouterLink, useRouter } from "vue-router"
import SearchBar from "@/components/SearchBar.vue"
import { isDesktop } from "@/composables/useMediaQuery"
import Drawer from "primevue/drawer"
import Button from "@/components/atoms/ButtonAtom.vue"
import NavigationListAtom from "@/components/atoms/NavigationListAtom.vue"

const router = useRouter()
const navMenuVisible = ref(false)
const searchMenuVisible = ref(false)

watch(router.currentRoute, closeDrawers)

function closeDrawers() {
  searchMenuVisible.value = false
  navMenuVisible.value = false
}
function toggleDrawer(name: string) {
  if (name == "navMenu") {
    searchMenuVisible.value = false
    navMenuVisible.value = !navMenuVisible.value
  } else {
    navMenuVisible.value = false
    searchMenuVisible.value = !searchMenuVisible.value
  }
}
</script>

<template>
  <header>
    <nav v-if="isDesktop" class="container d-flex">
      <RouterLink style="line-height: 0" to="/">
        <img class="logo" src="@/assets/img/logo_white.svg" />
      </RouterLink>
      <NavigationListAtom class="d-flex" style="gap: 0" />
      <SearchBar width="330px"></SearchBar>
    </nav>
    <nav v-else class="d-flex">
      <div id="nav-menu">
        <Button
          v-if="!navMenuVisible"
          id="navMenu"
          icon="bars"
          type="action"
          @click="toggleDrawer('navMenu')"
          custom-class="header-button"
        ></Button>
        <Button
          v-else
          id="navMenuClose"
          icon="xmark"
          type="action"
          @click="toggleDrawer('navMenu')"
          custom-class="header-button"
        ></Button>
        <Drawer
          v-model:visible="navMenuVisible"
          :baseZIndex="8000"
          :pt="{
            root: { class: 'top-drawer' },
          }"
        >
          <template #container>
            <NavigationListAtom class="nav-standalone d-flex" style="gap: 0" />
          </template>
        </Drawer>
      </div>
      <RouterLink style="line-height: 0" to="/">
        <img class="logo" src="@/assets/img/logo_white.svg" />
      </RouterLink>
      <div id="search-menu">
        <Button
          v-if="!searchMenuVisible"
          id="searchMenu"
          icon="magnifying-glass"
          type="action"
          custom-class="header-button"
          @click="toggleDrawer('searchMenu')"
        ></Button>
        <Button
          v-else
          id="searchMenuClose"
          icon="xmark"
          type="action"
          @click="toggleDrawer('searchMenu')"
          custom-class="header-button"
        ></Button>
        <Drawer
          v-model:visible="searchMenuVisible"
          position="right"
          :baseZIndex="8000"
          :pt="{
            root: { class: 'top-drawer' },
          }"
        >
          <template #container>
            <SearchBar width="500px"></SearchBar>
          </template>
        </Drawer>
      </div>
    </nav>
  </header>
</template>

<style scoped>
header {
  padding: 0 1rem;
  position: fixed;
  top: 0;
  width: 100%;
  background-color: var(--p-primary-800);
  z-index: 10000;
  height: var(--header-height);
  overflow: hidden;
}

nav {
  justify-content: space-between;
  align-items: center;
}

.logo {
  margin: 0.5rem 1rem;
  height: calc(var(--header-height) - 1rem);
  background-color: transparent;
}

.header-button {
  background-color: var(--p-primary-800);
  border-color: transparent;
  font-size: 1.5rem;
}
</style>
