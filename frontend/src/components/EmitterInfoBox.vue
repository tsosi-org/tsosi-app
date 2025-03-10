<script setup lang="ts">
import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"
import { RouterLink } from "vue-router"
import InfrastructurePopup from "@/components/InfrastructurePopup.vue"
</script>

<template>
  <section class="info-box">
    <div class="info-item">
      <h3>Data source</h3>
      <span>
        Only the data from TSOSI perimeter is
        <span style="white-space: nowrap">
          included.
          <InfoButtonAtom>
            <template #default>
              <InfrastructurePopup />
            </template>
          </InfoButtonAtom>
        </span>
      </span>
    </div>

    <div class="info-item">
      <h3>Disclosed amounts</h3>
      <span>
        The individual transfert amounts may not be disclosed depending on the
        supported infrastructure,
        <RouterLink to="/faq#partner-definition">see our FAQ</RouterLink>
      </span>
    </div>
  </section>
</template>
