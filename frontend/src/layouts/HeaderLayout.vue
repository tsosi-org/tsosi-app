<script setup lang="ts">
import { ref, watch } from "vue"
import { RouterLink, useRouter } from "vue-router"
import SearchBar from "@/components/SearchBar.vue"
import { isDesktop } from "@/composables/useMediaQuery"
import Drawer from "primevue/drawer"
import Button from "@/components/atoms/ButtonAtom.vue"

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
      <ul class="d-flex" style="gap: 0">
        <li>
          <RouterLink to="/about">Open Infrastructure</RouterLink>
        </li>
        <li>
          <RouterLink to="/">Supporter</RouterLink>
        </li>
        <li>
          <RouterLink to="/">FAQ</RouterLink>
        </li>
        <li>
          <RouterLink to="/about">About</RouterLink>
        </li>
      </ul>
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
            <ul class="nav-standalone d-flex">
              <li>
                <RouterLink to="/about">Open Infrastructure</RouterLink>
              </li>
              <li>
                <RouterLink to="/">Supporter</RouterLink>
              </li>
              <li>
                <RouterLink to="/">FAQ</RouterLink>
              </li>
              <li>
                <RouterLink to="/about">About</RouterLink>
              </li>
            </ul>
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

ul {
  padding: 0;
}

li {
  list-style: none;
}

li a {
  --this-fs: 20px;
  --this-lh: 1;
  line-height: var(--this-lh);
  font-size: var(--this-fs);
  display: block;
  text-decoration: none;
  color: var(--p-gray-50);
  padding: calc((var(--header-height) - var(--this-lh) * var(--this-fs)) / 2);
}

ul.nav-standalone {
  width: 100%;
  gap: 0;
  flex-direction: column;

  & li a {
    color: var(--p-color-primary);
  }
}

.header-button {
  background-color: var(--p-primary-800);
  border-color: transparent;
  font-size: 1.5rem;
}
</style>
