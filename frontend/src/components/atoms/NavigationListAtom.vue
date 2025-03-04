<script setup lang="ts">
import { RouterLink } from "vue-router"
</script>

<template>
  <ul>
    <li>
      <RouterLink to="/faq">FAQ</RouterLink>
    </li>
    <li>
      <RouterLink to="/about">About</RouterLink>
    </li>
  </ul>
</template>

<style scoped>
ul {
  padding: 0;
}

li {
  position: relative;
  list-style: none;
  --this-fs: 20px;
  --this-lh: 1;
}

li a {
  line-height: var(--this-lh);
  font-size: var(--this-fs);
  display: block;
  text-decoration: none;
  color: var(--p-gray-50);
  padding: calc((var(--header-height) - var(--this-lh) * var(--this-fs)) / 2);
}

li::after {
  content: "";
  --height: calc(var(--this-fs) - 2px);
  height: var(--height);
  /* width: 1px; */
  background-color: var(--p-gray-50);
  position: absolute;
  right: 0;
  top: calc((var(--header-height) - var(--height)) / 2 + 1px);
}

li:last-child::after {
  all: unset;
}

ul.nav-standalone {
  width: 100%;
  gap: 0;
  flex-direction: column;

  & li a {
    color: var(--p-color-primary);
  }
}
</style>
