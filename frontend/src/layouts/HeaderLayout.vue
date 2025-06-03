<script setup lang="ts">
import { ref, watch } from "vue"
import { RouterLink, useRouter } from "vue-router"
import SearchBar from "@/components/SearchBar.vue"
import { isDesktop } from "@/composables/useMediaQuery"
import Drawer from "primevue/drawer"
import Button from "@/components/atoms/ButtonAtom.vue"
import NavigationListAtom from "@/components/atoms/NavigationListAtom.vue"
import { $dt } from "@primevue/themes"
import { bigHeader } from "@/singletons/fixedHeaderStore"

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

/**
 * Toggle a custom class on the #body element to indicate an opened drawer.
 */
function onDrawerToggle(show: boolean) {
  const body = document.getElementById("body")
  if (show) {
    body!.classList.add("drawer-open")
  } else {
    body!.classList.remove("drawer-open")
  }
}
</script>

<template>
  <header
    id="header"
    class="header-visible"
    :class="{ home: bigHeader, desktop: isDesktop }"
  >
    <!-- Large screen header -->
    <nav v-if="isDesktop" class="container">
      <div class="logo-container" style="width: 330px">
        <RouterLink
          style="line-height: 0; display: block; width: fit-content"
          to="/"
          @click="closeDrawers"
        >
          <img class="logo" src="@/assets/img/logo_white.svg" />
        </RouterLink>
        <RouterLink to="/pages/faq#beta-version" class="beta-badge">
          Beta version
        </RouterLink>
      </div>

      <div v-show="bigHeader" class="header-citation">
        <h2>Transparency to Sustain Open Science Infrastructure</h2>
      </div>
      <div
        v-show="!bigHeader"
        style="
          display: flex;
          flex-direction: row;
          align-items: center;
          gap: 1.5rem;
          padding-right: 3rem;
        "
      >
        <SearchBar
          :place-holder="'Search for infrastructure or institution'"
          width="330px"
          :as-growing-button="false"
        />

        <NavigationListAtom
          :color="$dt('neutral.50').value"
          :header="true"
          font-size="20px"
          class="d-flex"
          style="gap: 0"
        />
      </div>
    </nav>

    <!-- Small screens header -->
    <nav v-if="!isDesktop">
      <div v-show="!bigHeader" id="nav-menu">
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
          @show="onDrawerToggle(true)"
          @hide="onDrawerToggle(false)"
        >
          <template #container>
            <NavigationListAtom
              :color="$dt('primary').value"
              font-size="20px"
              :header="true"
              class="nav-standalone d-flex"
              style="gap: 0"
            />
          </template>
        </Drawer>
      </div>

      <div class="logo-container">
        <RouterLink style="line-height: 0" to="/" @click="closeDrawers">
          <img class="logo" src="@/assets/img/logo_white.svg" />
        </RouterLink>
        <RouterLink to="/pages/faq#beta-version" class="beta-badge">
          Beta version
        </RouterLink>
      </div>
      <div v-show="bigHeader" class="header-citation">
        Transparency to Sustain Open Science Infrastructure
      </div>

      <div id="search-menu" v-show="!bigHeader">
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
          @show="onDrawerToggle(true)"
          @hide="onDrawerToggle(false)"
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
  padding: 0 min(1rem, 2vw);
  position: fixed;
  top: 0;
  width: 100%;
  background-color: var(--p-primary-800);
  z-index: 10000;
  height: var(--header-height);
  overflow: hidden;
  transform: translate(0, -100%);
  transition: all 0.2s ease-in-out;

  &.header-visible {
    transform: unset;
  }

  &.desktop {
    & .beta-badge {
      position: initial;
      right: unset;
      bottom: unset;
      transform: unset;
    }
  }
}

header.home {
  --content-height: calc(var(--header-height) - 6rem);
  padding: 1rem 1rem;
  transform: unset;

  & .logo {
    margin: 0;
    padding: 0 auto;
    max-width: 100%;
    margin-left: -4px;
    height: min(var(--content-height), 50px);
  }

  & nav {
    display: grid;
    grid-template-columns: 1fr;
    align-items: center;
    justify-items: center;
    column-gap: 2rem;
    margin: auto;
    height: 100%;
  }

  &.desktop {
    & .logo {
      height: min(var(--content-height), 100px);
      margin-left: 0;
    }

    & nav {
      font-size: 2.25rem;
      display: flex;
      justify-content: space-between;
      grid-template-columns: unset;
    }
  }
}

.header-citation,
.header-citation h2 {
  color: white;
  font-weight: 500;
  text-align: center;
  font-size: inherit;
}

.desktop .header-citation h2 {
  text-align: right;
  max-width: 500px;
}

nav {
  min-height: 100%;
  font-size: 1rem;
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.logo {
  height: calc(var(--header-height) - 1rem);
  background-color: transparent;
}

.header-button {
  background-color: var(--p-primary-800);
  border-color: transparent;
  font-size: 1.5rem;
}

.logo-container {
  position: relative;
  display: flex;
  align-items: end;
  gap: 0.5rem;
}

.beta-badge {
  font-size: 0.8rem;
  height: fit-content;
  background-color: #e5a722;
  color: white;
  padding: 1px 5px;
  border-radius: 4px;
  text-decoration: unset;
  /* Only for mobile */
  position: absolute;
  right: 0;
  bottom: 0;
  transform: translate(calc(100% + 0.5rem), 0);
}
</style>
