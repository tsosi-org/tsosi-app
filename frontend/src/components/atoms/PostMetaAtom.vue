<script setup lang="ts">

interface Props {
  date: Date
  readingTime: number
  author: string
}

const props = defineProps<Props>()

</script>

<template>
    <span>
      <font-awesome-icon :icon="['fas', 'calendar']" />
      Posted on {{ props.date.toISOString().split('T')[0] }} |
      <font-awesome-icon :icon="['fas', 'clock']" />
      {{ props.readingTime }} {{ props.readingTime > 1 ? 'minutes' : 'minute' }} |
      <font-awesome-icon :icon="['fas', 'user']" />
      {{ props.author }}
    </span>
</template>