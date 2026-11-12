<script setup lang="ts">
import { ref } from "vue"

import {
  type NewsletterAction,
  requestNewsletter,
} from "@/singletons/newsletter"

// Form (un)subscribing an e-mail to the newsletter, applied right away.
const props = withDefaults(defineProps<{ action?: NewsletterAction }>(), {
  action: "subscribe",
})

const TEXTS = {
  subscribe: {
    button: "Subscribe",
    done: "You're subscribed to the TSOSI newsletter!",
  },
  unsubscribe: {
    button: "Unsubscribe",
    done: "You're unsubscribed from the TSOSI newsletter.",
  },
}
const text = TEXTS[props.action]

const email = ref("")
const state = ref<"idle" | "sending" | "sent">("idle")
const error = ref<string | null>(null)

async function onSubmit() {
  state.value = "sending"
  error.value = await requestNewsletter(props.action, email.value)
  state.value = error.value ? "idle" : "sent"
}
</script>

<template>
  <div class="newsletter-sub">
    <div v-if="state === 'sent'" role="status">
      <p class="label">{{ text.done }}</p>
    </div>
    <form v-else class="newsletter-form" @submit.prevent="onSubmit">
      <div class="fields">
        <input
          v-model="email"
          class="email-input"
          type="email"
          name="email"
          placeholder="your@email.org"
          autocomplete="email"
          required
          :disabled="state === 'sending'"
        />
        <button
          class="special-button"
          type="submit"
          :disabled="state === 'sending'"
        >
          {{ text.button }}
        </button>
      </div>
      <p v-if="error" class="error" role="alert">
        {{ error }}
      </p>
    </form>
  </div>
</template>

<style scoped>
.newsletter-sub {
  text-align: center;
}

.newsletter-form {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  max-width: 100%;
}

.label {
  font-size: var(--text-lg);
}

.fields {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 0.5rem;
  max-width: 100%;
}

.email-input {
  flex: 1 1 16rem;
  min-width: 0;
  padding: 0.6rem 0.75rem;
  font-size: var(--text-base);
  border: 2px solid var(--p-primary-600);
  border-radius: 4px;
}

.error {
  color: var(--p-red-600);
}

.special-button {
  --color-1: var(--p-primary-600);
  --color-2: var(--p-primary-700);
  --color-invert: white;
  padding: 0.6rem 1.25rem;
  font-size: var(--text-base);
  border: 2px solid var(--color-1);
  background-color: var(--color-1);
  color: var(--color-invert);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease-out;

  &:hover:not(:disabled) {
    border-color: var(--color-2);
    background-color: var(--color-2);
  }

  &:disabled {
    opacity: 0.7;
    cursor: wait;
  }
}
</style>
