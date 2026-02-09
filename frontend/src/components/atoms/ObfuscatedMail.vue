<script setup lang="ts">
import { onMounted } from "vue"

const props = defineProps<{ mail: string }>()

const rot13 = (message: string): string => {
  const originalAlpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  const cipher = "nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM"
  return message.replace(
    /[a-z]/gi,
    (letter) => cipher[originalAlpha.indexOf(letter)],
  )
}

onMounted(() => {
  const emailLink = document.getElementById("emailLinkID") as HTMLAnchorElement
  emailLink.href = `mailto:${rot13(props.mail)}`
  emailLink.textContent = rot13(props.mail)
})
</script>

<template>
  <a id="emailLinkID"></a>
</template>
