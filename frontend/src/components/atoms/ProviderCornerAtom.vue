<script setup lang="ts"></script>

<template>
  <div class="corner-container" v-tooltip.top="'TSOSI\'s data provider'">
    <img
      src="@/assets/img/tsosi_provider_simple.svg"
      alt="TSOSI\'s data provider"
    />
  </div>
</template>

<style scoped>
.corner-container {
  width: 0;
  height: 0;
  border-top: 45px solid #216d95;
  border-left: 45px solid transparent;
  position: absolute;
  top: 0;
  right: 0;
  filter: drop-shadow(-2px -2px 3px rgba(0, 0, 0, 0.3));
}

.corner-container img {
  position: absolute;
  top: -38px;
  right: 2px;
  width: 18px;
  height: 18px;
}
</style>
