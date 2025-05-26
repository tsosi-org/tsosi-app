<script setup lang="ts">
import InfoButtonAtom from "@/components/atoms/InfoButtonAtom.vue"
import { RouterLink } from "vue-router"
import InfrastructurePopup from "@/components/InfrastructurePopup.vue"
import Panel from "primevue/panel"
</script>

<template>
  <Panel toggleable class="info-box">
    <template #header>
      <h2 class="info-box-header">Data coverage</h2>
    </template>
    <div class="info-item">
      <h3>Data source</h3>
      <span>
        Only the data from TSOSI perimeter is
        <span style="white-space: nowrap">
          included.
          <InfoButtonAtom>
            <template #popup>
              <InfrastructurePopup />
            </template>
          </InfoButtonAtom>
        </span>
      </span>
    </div>

    <div class="info-item">
      <h3>Disclosed amounts</h3>
      <span>
        The individual transfer amounts may not be disclosed depending on the
        supported infrastructure,
        <RouterLink to="/pages/faq#amounts-hidden">see our FAQ</RouterLink>.
      </span>
    </div>
  </Panel>
</template>
