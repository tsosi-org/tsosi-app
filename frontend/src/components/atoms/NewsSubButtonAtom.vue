<script setup lang="ts">
import ExternalLinkAtom from "./ExternalLinkAtom.vue";


const subscription_url = import.meta.env.VITE_NEWSLETTERS_SUBSCRIPTION_URL
</script>

<template>
  <div v-if="subscription_url" class="container">
    <ExternalLinkAtom class="special-button" :href="subscription_url">
      Subscribe to our
      <span style="white-space: nowrap">
        Newsletter
        <font-awesome-icon :icon="['fas', 'arrow-up-right-from-square']" />
      </span>
    </ExternalLinkAtom>
  </div>

  <div v-else class="container">
    <p>Newsletter subscription is currently unavailable.</p>
  </div>
</template>


<style scoped>
.container {
  text-align: center;
  font-size: 1.5rem;
  padding: 1rem 0;
}

.link-icon {
  margin-right: 0.5rem;
}

.special-button {
  --color-1: var(--p-primary-600);
  --color-2: var(--p-primary-700);
  --color-invert: white;
  display: inline-block;
  column-gap: 1em;
  align-items: baseline;
  padding: 0.6rem 1.25rem;
  border: 2px solid var(--color-1);
  background-color: var(--color-1);
  color: var(--color-invert);
  border-radius: 4px;
  text-decoration: unset;
  transition: all 0.2s ease-out;

  &>.fa-icon {
    margin-left: 0.75rem;
  }
}
</style>