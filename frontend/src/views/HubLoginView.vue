<script setup lang="ts">
import Button from "primevue/button"
import InputText from "primevue/inputtext"
import { onMounted, ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import Message from "@/components/atoms/MessageAtom.vue"
import { changeMetaTitle } from "@/utils/seo"
import {
  hasLoginToken,
  hubNextPath,
  loadSession,
  logIn,
  requestLoginLink,
} from "@/singletons/hub-session"

const route = useRoute()
const router = useRouter()

changeMetaTitle("Data Contribution Hub login")

const email = ref("")
const sending = ref(false)
const sentTo = ref<string | null>(null)
const error = ref<string | null>(null)
const withToken = ref(hasLoginToken())
const loggingIn = ref(false)

// The Hub page asked before the login, with its query (see `hubGuard`)
function nextRoute(): string {
  return hubNextPath(route.query.next) ?? "/hub"
}

onMounted(async () => {
  if (!withToken.value && (await loadSession())) {
    router.replace(nextRoute())
  }
})

async function sendLink() {
  error.value = null
  sending.value = true
  // The link leads back to the page asked, even opened in a new tab
  const status = await requestLoginLink(email.value.trim(), nextRoute())
  sending.value = false
  if (status == 204) {
    sentTo.value = email.value.trim()
  } else if (status == 400) {
    error.value = "Enter a valid e-mail address."
  } else if (status == 429) {
    error.value = "Too many login requests. Please try again later."
  } else {
    error.value = "The login link couldn't be sent. Please try again later."
  }
}

async function logInWithLink() {
  loggingIn.value = true
  const ok = await logIn()
  loggingIn.value = false
  if (ok) {
    router.replace(nextRoute())
  } else {
    withToken.value = false
    error.value =
      "This login link is invalid or expired. Ask for a new one below."
  }
}
</script>

<template>
  <div class="container small">
    <div class="regular-content hub-login">
      <div class="login-card">
        <h1>Log in</h1>
        <template v-if="withToken">
          <p>Log in to the TSOSI Data Contribution Hub.</p>
          <Button label="Log in" :loading="loggingIn" @click="logInWithLink" />
        </template>
        <Message v-else-if="sentTo" severity="success">
          If {{ sentTo }} belongs to a data provider organization, we sent a
          login link to it. It's valid for 15 minutes.
        </Message>
        <form v-else @submit.prevent="sendLink">
          <Message v-if="error" severity="error">{{ error }}</Message>
          <label for="hub-email">E-mail</label>
          <InputText
            id="hub-email"
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="name@institution.edu"
            required
          />
          <Button
            type="submit"
            label="Send me a login link"
            :loading="sending"
          />
        </form>
      </div>
      <!-- Not needed when coming from a login link -->
      <p v-if="!withToken" class="info-box">
        Only members of data provider organizations can log in. See how to
        <RouterLink :to="{ name: 'new-provider' }">become one</RouterLink>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.hub-login {
  max-width: 460px;
  margin: 3rem auto !important;
  display: flex !important;
  flex-direction: column;
  gap: 1.25rem;
}

.login-card,
.login-card form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-card {
  padding: 2rem;
  /* Same frame as the info boxes */
  border: 3px solid var(--p-surface-200);
  border-radius: 5px;
}

h1 {
  margin: 0;
}

label {
  color: var(--color-heading);
  font-weight: 600;
  margin-bottom: -0.5rem;
}

.info-box {
  margin: 0;
}
</style>
