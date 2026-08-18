<script setup lang="ts">
import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue";
import { useContactModal } from "@/composables/useContactModal";
import { changeMetaTitle } from "@/utils/dom-utils";
import { useRoute } from "vue-router";
const { openContactModal } = useContactModal()

const route = useRoute()

changeMetaTitle("404 Not found")
const query = route.query
const queriedUrl = query.target || route.path
const params = {
  content: queriedUrl as string,
  inline: true,
  background: true,
}
</script>

<template>
  <div class="container">
    <div class="regular-content">
      <h1>404 - Not found</h1>
      <div class="not-found">
        <p>The queried URL
          <CodeBlockAtom v-bind="params" /> does not exist.
        </p>
        <span>
          <a @click="openContactModal">Contact us</a> if you think this is an error.
        </span>
        <p>Go back to the <RouterLink :to="'/'">home page</RouterLink>.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 {
  text-align: center;
  font-size: 3rem;
}

.not-found {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 3rem;
}
</style>
