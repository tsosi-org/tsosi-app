<script setup lang="ts">
import Divider from "primevue/divider"
import { onBeforeMount, ref, type Ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import Loader from "@/components/atoms/LoaderAtom.vue"
import Breadcrumb, {
  type BreadcrumbItem,
} from "@/components/BreadcrumbComponent.vue"
import Summary from "@/components/SummaryComponent.vue"
import { isDesktop } from "@/composables/useMediaQuery"
import {
  getTransferDetails,
  type Entity,
  type TransferDetails,
} from "@/singletons/ref-data"
import { type DataFieldProps } from "@/utils/data-utils"
import { getEntityBaseUrl, getEntityUrl } from "@/utils/url-utils"


const route = useRoute()
const router = useRouter()
const transfer: Ref<TransferDetails | null> = ref(null)
const loading = ref(true)

const breadcrumb: Ref<Array<BreadcrumbItem> | null> = ref(null)

onBeforeMount(async () => {
  const result = await getTransferDetails(route.params.id as string)
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  transfer.value = result

  breadcrumb.value = [
    {
      label: "Home",
      route: "/",
      icon: ["fas", "house"],
    },
    {
      label: transfer.value.recipient!.name,
      route: getEntityUrl(transfer.value.recipient! as Entity),
      icon: ["fas", "building-columns"],
    },
    {
      label: transfer.value.id,
      route: route.path,
      icon: ["fas", "magnifying-glass-chart"],
    },
  ]

  loading.value = false
})

const dataConfig: Array<DataFieldProps> = [
  {
    id: "id",
    title: "ID",
    field: "id",
    type: "string",
  },
  {
    id: "emitter",
    title: "Emitter",
    field: "emitter",
    type: "entityLink",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "emitter.id",
      suffixType: "field",
    },
  },
  {
    id: "emitterCountry",
    title: "Country",
    field: "emitter.country",
    type: "country",
  },
  {
    id: "recipient",
    title: "Recipient",
    field: "recipient",
    type: "entityLink",
    fieldLabel: "recipient.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "recipient.id",
      suffixType: "field",
    },
  },
  {
    id: "agent",
    title: "Intermediary",
    field: "agent",
    type: "entityLink",
    fieldLabel: "agent.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "agent.id",
      suffixType: "field",
    },
  },
  {
    id: "amount",
    title: "Amount",
    field: "amount",
    type: "number",
  },
  {
    id: "currency",
    title: "Currency",
    field: "currency",
    type: "string",
  },
  {
    id: "dateClc",
    title: "Date computed",
    field: "date_clc",
    type: "dateWithPrecision",
  },
  {
    id: "dateAgreement",
    title: "Date agreement",
    field: "date_agreement",
    type: "dateWithPrecision",
  },
  {
    id: "dateInvoice",
    title: "Date invoice",
    field: "date_invoice",
    type: "dateWithPrecision",
  },
  {
    id: "datePaymentRecipient",
    title: "Date payment received",
    field: "date_payment_recipient",
    type: "dateWithPrecision",
  },
  {
    id: "datePaymentEmitter",
    title: "Date payment emitted",
    field: "date_payment_emitter",
    type: "dateWithPrecision",
  },
  {
    id: "dateStart",
    title: "Date start",
    field: "date_start",
    type: "dateWithPrecision",
  },
  {
    id: "dateEnd",
    title: "Date end",
    field: "date_end",
    type: "dateWithPrecision",
  },
]

const metadataConfig: Array<DataFieldProps> = [
  {
    id: "source",
    title: "Source",
    field: "source",
    type: "string",
  },
  {
    id: "amountsClc",
    title: "Converted amounts",
    field: "amounts_clc",
    type: "json",
  },
  {
    id: "rawData",
    title: "Raw data",
    field: "raw_data",
    type: "json",
  },
]
</script>

<template>
  <Loader v-if="loading" width="150px" />
  <div v-if="transfer" class="container">
    <div class="regular-content">
      <Breadcrumb v-if="breadcrumb" :items="breadcrumb" />
      <h1 style="margin: 1.5rem 0.5rem">Transfer details</h1>
      <div class="data-layout" :class="{ desktop: isDesktop }">
        <div class="data-content">
          <h2 class="summary-title">Data</h2>
          <Summary :data="transfer" :fields="dataConfig" :explicit="true" />
        </div>
        <Divider :layout="isDesktop ? 'vertical' : 'horizontal'" />
        <div>
          <h2 class="summary-title">Metadata</h2>
          <Summary :data="transfer" :fields="metadataConfig" :explicit="true" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-layout.desktop {
  display: flex;
}

.data-content {
  flex: 0 0 50%;
}

.summary-title {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
  margin-left: min(10%, 50px);
  text-decoration: underline;
}
</style>
