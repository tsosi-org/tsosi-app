<script lang="ts" setup>
const props = defineProps<{ width?: string }>()
</script>

<template>
  <div class="card" :class="{ width: props.width != undefined }">
    <div class="card-header">
      <slot name="header"> </slot>
    </div>
    <div class="card-body">
      <div class="card-title" style="text-align: center">
        <slot name="title"></slot>
      </div>
      <div class="card-content">
        <slot name="content"> </slot>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  position: relative;
  width: v-bind(width);
  min-height: 5rem;

  background: white;
  box-shadow:
    rgba(0, 0, 0, 0.1) 0px 1px 3px 0px,
    rgba(0, 0, 0, 0.1) 0px 1px 2px -1px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;

  &.width {
    width: v-bind(width);
  }
}

.card-header {
  display: flex;
  place-content: center;
}

.card-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 500;
}

.card-content {
  padding: 0 2em;
}
</style>
