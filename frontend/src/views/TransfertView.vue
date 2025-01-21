<script setup lang="ts">
import { onBeforeMount, ref, type Ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Divider from "primevue/divider"
import {
  getTransfertDetails,
  type TransfertDetails,
} from "@/singletons/ref-data"
import { getEntityBaseUrl, getEntityUrl } from "@/utils/url-utils"
import { type DataFieldProps } from "@/utils/data-utils"
import Summary from "@/components/SummaryComponent.vue"
import Loader from "@/components/atoms/LoaderAtom.vue"
import Breadcrumb, {
  type BreadcrumbItem,
} from "@/components/BreadcrumbComponent.vue"
import { useMediaQuery } from "@/composables/useMediaQuery"

const route = useRoute()
const router = useRouter()
const transfert: Ref<TransfertDetails | null> = ref(null)
const loading = ref(true)

const breadcrumb: Ref<Array<BreadcrumbItem> | null> = ref(null)

onBeforeMount(async () => {
  const result = await getTransfertDetails(route.params.id as string)
  if (result == null) {
    router.replace({ name: "NotFound", query: { target: route.path } })
    return
  }
  transfert.value = result

  breadcrumb.value = [
    {
      label: "Home",
      route: "/",
      icon: "house",
    },
    {
      label: transfert.value.recipient!.name,
      route: getEntityUrl(transfert.value.recipient!.id),
      icon: "building-columns",
    },
    {
      label: transfert.value.id,
      route: route.path,
      icon: "magnifying-glass-chart",
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
    type: "pageLink",
    fieldLabel: "emitter.name",
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
    type: "pageLink",
    fieldLabel: "recipient.name",
    fieldLink: {
      base: getEntityBaseUrl(),
      suffix: "recipient.id",
      suffixType: "field",
    },
  },
  {
    id: "agent",
    title: "Agent",
    field: "agent",
    type: "pageLink",
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
    id: "datePayment",
    title: "Date payment",
    field: "date_payment",
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

const desktop = useMediaQuery("(min-width: 1000px)")
</script>

<template>
  <Loader v-if="loading" width="150px" />
  <div v-if="transfert" class="container">
    <div class="regular-content">
      <Breadcrumb v-if="breadcrumb" :items="breadcrumb" />
      <h1 style="margin: 1.5rem 0.5rem">Transfert details</h1>
      <div class="data-layout" :class="{ desktop: desktop }">
        <div class="data-content">
          <h2 class="summary-title">Data</h2>
          <Summary :data="transfert" :fields="dataConfig" :explicit="true" />
        </div>
        <Divider :layout="desktop ? 'vertical' : 'horizontal'" />
        <div>
          <h2 class="summary-title">Metadata</h2>
          <Summary
            :data="transfert"
            :fields="metadataConfig"
            :explicit="true"
          />
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
