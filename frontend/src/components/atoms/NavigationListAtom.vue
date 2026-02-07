<script setup lang="ts">
import { RouterLink } from "vue-router";



const props = defineProps<{
  color: string
}>()
</script>

<template>
  <div class="nagivation-list">
    <ul>
      <li>
        <RouterLink to="/pages/about">About</RouterLink>
      </li>
      <li>
        <RouterLink to="/pages/faq">FAQ</RouterLink>
      </li>
      <li>
        <ExternalLinkAtom
        :href="'https://blog.tsosi.org'"
        :label="'Blog'"
        :target="'_self'"
        />
      </li>
    </ul>
  </div>
</template>

<style scoped>
ul {
  --local-color: v-bind(props.color);
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
  padding: 15px;
}

li::after {
  content: "";
  --height: calc(var(--this-fs) - 2px);
  height: var(--height);
  /* width: 1px; */
  background-color: var(--local-color);
  position: absolute;
  right: 0;
}

li:last-child::after {
  all: unset;
}

div.nav-standalone {
  width: 100%;
  gap: 0;
  flex-direction: column;
}
</style>
