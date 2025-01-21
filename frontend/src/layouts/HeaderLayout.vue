<script setup lang="ts">
import { RouterLink } from "vue-router"
import SearchBar from "@/components/SearchBar.vue"
</script>

<template>
  <header>
    <nav class="container d-flex">
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
      <SearchBar></SearchBar>
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
</style>
