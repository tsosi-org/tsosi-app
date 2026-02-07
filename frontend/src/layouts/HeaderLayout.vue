<script setup lang="ts">
import { $dt } from "@primevue/themes"
import Drawer from "primevue/drawer"
import { ref, watch } from "vue"
import { RouterLink, useRouter } from "vue-router"

import Button from "@/components/atoms/ButtonAtom.vue"
import NavigationListAtom from "@/components/atoms/NavigationListAtom.vue"
import SearchBar from "@/components/SearchBar.vue"
import { isDesktop } from "@/composables/useMediaQuery"
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
    :class="{ home: bigHeader, mobile: !isDesktop }"
  >
    <!-- Large screen header -->
    <div v-if="isDesktop" class="container">
      <div class="left-container">
      <div class="logo-container">
        <RouterLink
          to="/"
          @click="closeDrawers"
          class="logo"
        >
          <img class="logo-img" src="@/assets/img/logo_white.svg" />
        </RouterLink>
        <RouterLink to="/pages/faq#beta-version" class="beta-badge">
          beta version
        </RouterLink>
      </div>
      <div class="header-citation">
        <h2>Transparency to Sustain Open Science Infrastructure</h2>
      </div>
      </div>

      <div class="right-container">
        <div class="header-nav">
          <SearchBar
            :fixed="true"
            :place-holder="'Search for supporters or infrastructures'"
            width="330px"
            :as-growing-button="false"
          />

          <NavigationListAtom/>
        </div>
        </div>
    </div>

    <!-- Small screens header -->
    <div v-if="!isDesktop" class="container">
      <div id="nav-menu" class="button-container">
        <Button
          v-if="!navMenuVisible"
          id="navMenu"
          :icon="['fas', 'bars']"
          type="action"
          @click="toggleDrawer('navMenu')"
          custom-class="header-button"
        ></Button>
        <Button
          v-else
          id="navMenuClose"
          :icon="['fas', 'xmark']"
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
              @click="closeDrawers"
            />
          </template>
        </Drawer>
      </div>

      <div class="main-container">
        <div class="logo-container">
          <RouterLink
            to="/"
            @click="closeDrawers"
            class="logo"
          >
            <img class="logo-img" src="@/assets/img/logo_white.svg" />
          </RouterLink>
          <RouterLink to="/pages/faq#beta-version" class="beta-badge">
            beta version
          </RouterLink>
        </div>
        <div class="header-citation">
          <h2>Transparency to Sustain Open Science Infrastructure</h2>
        </div>
      </div>

      <div id="search-menu" class="button-container">
        <Button
          v-if="!searchMenuVisible"
          id="searchMenu"
          :icon="['fas', 'magnifying-glass']"
          type="action"
          custom-class="header-button"
          @click="toggleDrawer('searchMenu')"
        ></Button>
        <Button
          v-else
          id="searchMenuClose"
          :icon="['fas', 'xmark']"
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
            <SearchBar
              :fixed="true"
              width="500px"
              :place-holder="'Search for supporters or infrastructures'"
            ></SearchBar>
          </template>
        </Drawer>
      </div>
    </div>
  </header>
</template>

<style scoped>

header {
  position: fixed;
  display: flex;
  align-items: center;
  justify-content: center;
  top: 0;
  width: 100%;
  background-color: var(--p-primary-800);
  z-index: 10000;
  height: var(--big-header-height);
  transform: translateY(-100px);
  transition: transform 0.2s ease-in-out;
}

header.home {
  transform: translateY(0);
}

.container {
  display: flex;
  height: 50px;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  transform: translateY(50px);
  transition: transform 0.2s ease-in-out;
}

.home .container {
  transform: translateY(0);
}

.left-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: start;
  justify-content: center;
  margin-left: 15px;
}

.main-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.right-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.logo-container {
  display: flex;
  align-items: end;
  height: 36px;

  .logo {
    height: 100%;

    .logo-img {
      height: 100%;
    }
  }

}

.home .logo-container {
  height: 66px;
}

.beta-badge {
  white-space: nowrap;
  font-size: 0.8rem;
  background-color: #e5a722;
  color: white;
  padding: 1px 5px;
  margin-left: 0.8rem;
  border-radius: 4px;
  text-decoration: unset;
}

.header-citation {
  display: none;
  margin-top: 15px;

  h2 {
    color: white;
    font-weight: 500;
    font-size: 12px;
  }
}

.home .header-citation {
    display: inline;
}


.header-nav {
  display: flex;
  flex-direction: row;
  align-items: center;
  margin-right: 15px;

  .search-bar {
    margin-right: 15px;
  }

  :deep(ul) {
    display: flex;
    list-style: none;
    padding: 0;
    margin-left: 15px;

    :deep(a), :deep(a):hover {
      line-height: 1;
      font-size: 20px;
      display: block;
      text-decoration: none;
      color: var(--p-neutral-50);
      padding: 15px;
    }
  }
}

.header-button {
  background-color: var(--p-primary-800);
  border-color: transparent;
  font-size: 1.5rem;
  margin: 0 13px;
  height: 50px;
}

@media (max-width: 500px) {
  .home .logo-container, .logo-container {
    height: 20px;
  }

  .logo-container .beta-badge {
    white-space: nowrap;
    font-size: 0.5rem;
    padding: 1px 3px;
    margin-left: 0.5rem;
    border-radius: 2px;
  }
  .home .header-citation {
      display: none;
  }
}

</style>
