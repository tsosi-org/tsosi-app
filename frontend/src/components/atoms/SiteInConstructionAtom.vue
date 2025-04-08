<script setup lang="ts">
import CodeBlockAtom from "./CodeBlockAtom.vue"
</script>

<template>
  <div class="wrapper">
    <div class="message">
      <h1>Welcome on TSOSI!</h1>
      <div>
        <p>
          You are going to navigate on a website in development ; the
          information is not yet stabilised. Please be indulgent and feel free
          to contact us for any feedback.
          <br />
          <br />
        </p>
        <CodeBlockAtom :content="'contact @(tsosi.org)'" />
      </div>
      <p>Enjoy your visit!</p>
    </div>
  </div>
</template>

<style scoped>
.wrapper {
  position: relative;
  padding: min(5px, 1vw);
}

.message {
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  font-size: 2rem;
  max-width: min(90vw, 800px);
  height: max(500px, 70vh);
  text-align: center;
}
</style>
