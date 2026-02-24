<script setup lang="ts">
import ObfuscatedMail from "@/components/atoms/ObfuscatedMail.vue"
import { useContactModal } from "@/composables/useContactModal"
import { watch } from "vue"

import Dialog from "primevue/dialog"
import { RouterLink, useRouter } from "vue-router"
import ExternalLinkAtom from "./atoms/ExternalLinkAtom.vue"
const router = useRouter()

const { isContactModalOpen, closeContactModal } = useContactModal()
watch(router.currentRoute, () => {
  if (isContactModalOpen.value) {
    closeContactModal()
  }
})
</script>

<template>
  <div class="container">
    <Dialog
      v-model:visible="isContactModalOpen"
      modal
      dismissableMask
      :draggable="false"
      :style="{ width: '45rem', padding: '1.5rem' }"
      :pt="{ mask: { style: { backdropFilter: 'blur(4px)' } } }"
      v-on:hide="closeContactModal"
    >
      <template #header>
        <h2>Contact</h2>
      </template>

      <div class="contact-body">
        <!-- Email section -->
        <div class="contact-section">
          <p class="contact-label">We look forward to hearing from you at</p>
          <ObfuscatedMail mail="pbagnpg@gfbfv.bet" class="contact-email" />
        </div>

        <hr class="divider" />

        <!-- Newsletter & Social section -->
        <div class="contact-section">
          <p class="contact-label">
            📣 Sign up for the
            <RouterLink
              @click="closeContactModal"
              to="/pages/newsletter"
              class="contact-link"
            >
              newsletter</RouterLink
            >.
          </p>
          <p class="contact-label">
            <font-awesome-icon :icon="['fab', 'linkedin']" class="link-icon" />
            Follow us on
            <ExternalLinkAtom
              :label="'LinkedIn'"
              :href="'https://www.linkedin.com/company/tsosi/'"
              class="contact-link"
            />.
          </p>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<style scoped>
.contact-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.5rem 0;
}

.link-icon {
  margin: 0 0.21rem;
}

.contact-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.contact-label {
  font-size: 1.15rem;
  font-weight: normal;
  margin: 0;
  color: var(--color-text);
}

.contact-email {
  font-size: 2rem;
  font-weight: bold;
  text-decoration: none;
  color: var(--p-primary-600);
}
.contact-email:hover {
  color: var(--p-primary-700);
}

.divider {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0.25rem 0;
}
</style>
