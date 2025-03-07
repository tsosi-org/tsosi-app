<script setup lang="ts">
import { RouterLink } from "vue-router"

const props = defineProps<{
  color?: string
  fontSize?: string
  header?: boolean
}>()
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
  --local-color: v-bind($props.color);
  --this-lh: 1;
  --this-fs: 20px;
  padding: 0;
}

li {
  position: relative;
  list-style: none;
}

a {
  line-height: var(--this-lh);
  font-size: var(--this-fs);
  display: block;
  text-decoration: none;
  color: var(--local-color);
  padding: calc((var(--header-height) - var(--this-lh) * var(--this-fs)) / 2);
}

li::after {
  content: "";
  --height: calc(var(--this-fs) - 2px);
  height: var(--height);
  /* width: 1px; */
  background-color: var(--local-color);
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
}
</style>
