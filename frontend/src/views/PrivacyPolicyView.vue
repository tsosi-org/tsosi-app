<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from "vue"

import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import { useContactModal } from "@/composables/useContactModal"
import StaticContentComponent from "@/views/StaticContentView.vue"

const { openContactModal } = useContactModal()

const matomoCheckboxValue = ref(false)
const optOutStatus = ref(false)
const matomoTracker = inject("Matomo")
const matomoOptOutLabel = computed(() =>
  optOutStatus.value
    ? "You are currently opted out. Uncheck this box to opt-in. "
    : "You are not opted out. Check this box to opt-out.",
)

watch(optOutStatus, () => {
  matomoCheckboxValue.value = optOutStatus.value
})

onMounted(() => {
  const status = isOptedOut()
  if (status !== undefined) {
    optOutStatus.value = status
  }
})

function toggleOptOut() {
  const status = isOptedOut()
  if (status === undefined) {
    return
  }
  if (isOptedOut()) {
    // @ts-expect-error matomo plugin has no types
    matomoTracker.forgetUserOptOut()
    optOutStatus.value = false
  } else {
    // @ts-expect-error matomo plugin has no types
    matomoTracker.optUserOut()
    optOutStatus.value = true
  }
}

function isOptedOut(): boolean | undefined {
  if (!matomoTracker) {
    console.log("Matomo tracker is not available.")
    return undefined
  }
  // @ts-expect-error matomo plugin has no types
  return matomoTracker.isUserOptedOut()
}
</script>

<template>
  <StaticContentComponent title="Privacy policy">
    <template #default>
      <p>
        The TSOSI project's mission is to foster the sustainability of open
        science infrastructures. In this context, Université Grenoble Alpes is
        required to collect and use personal information such as IP addresses,
        browsers, and the terminals used, as well as the e-mail addresses of the
        members of the Data Contribution Hub.
        <br />
        The personal information collected is processed in accordance with the
        General Data Protection Regulation (EU) 2016/679 of the European
        Parliament and of the Council of April 27, 2016 (GDPR), as well as the
        'Informatique et libertés' law of January 6, 1978, as amended.
      </p>

      <StaticSectionAtom
        id="data-collection-purpose"
        title="Purpose of data collection"
      >
        <p>The data we collect is used for the following purposes:</p>
        <ul>
          <li>
            <strong>Website analytics</strong>
            <br />
            To analyze and monitor website traffic, including the number of
            visitors, their location and the pages accessed.
          </li>
          <li>
            <strong>Troubleshooting and security</strong>
            <br />
            To identify and resolve any technical issues with the website, as
            well as to detect and prevent any security incidents.
          </li>
          <li>
            <strong>Newsletter</strong>
            <br />
            To send the TSOSI newsletter to the people who subscribed to it on
            this website. This processing is based on your consent, which you
            can withdraw at any time by unsubscribing.
          </li>
          <li>
            <strong>Data Contribution Hub</strong>
            <br />
            To give the members of an organization access to its space on the
            Data Contribution Hub, where they declare its supports and edit its
            public page, to send them their login links, and to keep track of
            the changes they make.
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom id="collected-data" title="Collected data">
        <p>We collect basic browsing logs when you visit our website:</p>
        <ul>
          <li>Your IP address</li>
          <li>Date</li>
          <li>Request made (in the form of a URL)</li>
          <li>Browser type</li>
          <li>Response status (HTTP status code)</li>
        </ul>

        <p v-if="matomoTracker">
          We aggregate and analyze the actions you take on our website using
          <ExternalLinkAtom :href="'https://matomo.org'" :label="'Matomo'" />.
          <br />
          We collect the following data:
        </p>
        <ul v-if="matomoTracker">
          <li>Your anonimized IP address</li>
          <li>The date</li>
          <li>The performed action (click, download, navigation)</li>
          <li>The URL of the page where you performed the action</li>
        </ul>

        <p>
          When you subscribe to the newsletter, we collect your e-mail address.
        </p>
        <p>
          If you are a member of the Data Contribution Hub, we store your e-mail
          address, the organization you are a member of and your access rights,
          and the changes you make to its supports and public page, linked to
          your account. Your IP address is also used, for one hour, to limit the
          number of login link requests.
        </p>
        <p>
          The Hub uses two cookies, needed for it to work, which require no
          consent: a session cookie, which keeps you logged in for 24 hours at
          most, and a security cookie (CSRF), which protects your actions
          against cross-site request forgery.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="collected-data-recipient"
        title="Recipient of the data collection"
      >
        <p>
          The data we collect is only used by the members of the TSOSI project
          to perform the previously listed tasks.
          <br />
          The data is stored on the information technology servers of the
          Université Grenoble Alpes.
        </p>
        <p>
          The e-mail addresses of the newsletter's subscribers are stored on the
          mailing list server of the Université Grenoble Alpes (Sympa), which
          sends the newsletter. Only the TSOSI team members who manage the list
          can see them. They are never shared with third parties.
        </p>
        <p>
          The e-mails of the Data Contribution Hub (login links and invitations)
          are sent through
          <ExternalLinkAtom :href="'https://www.brevo.com'" :label="'Brevo'" />,
          an e-mail delivery service, which processes your e-mail address and
          the content of these e-mails on our behalf.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="data-retention" title="Data retention">
        <p>
          We retain the logged data only for as long as necessary for the
          purposes stated above. This data is kept for a period not exceeding 24
          months, after which it is securely deleted.
        </p>
        <p>
          Your e-mail address is kept on the newsletter's mailing list as long
          as you are subscribed, and deleted from it when you unsubscribe.
        </p>
        <p>
          Your Data Contribution Hub account is kept as long as you are a member
          of an organization on the Hub, and deleted on request. The changes you
          made stay in the history of the published data, no longer linked to
          your account once it is deleted.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="data-your-rights" title="Your rights">
        <p>
          You have the right to access, rectify, erase, limit, and the right to
          data portability concerning your information, which you can exercise
          by contacting:
          <br />
          <br />
          Université Grenoble Alpes
          <br />
          GRICAD
          <br />
          150 place du Torrent 38400
          <br />
          Saint Martin d'Hères, France
          <br />
          <br />
          <a @click="openContactModal">Contact TSOSI</a>
        </p>
        <p>
          You can unsubscribe from the newsletter at any time from the link in
          each newsletter or on the
          <RouterLink to="/pages/newsletter/unsubscribe"
            >unsubscribe page</RouterLink
          >.
        </p>
        <p v-if="matomoTracker">
          <br />
          Additionally, you may choose to prevent this website from aggregating
          and analyzing the actions you take here. Doing so will protect your
          privacy, but will also prevent TSOSI from learning from your actions
          and creating a better experience for you and other users.
        </p>
        <p v-if="matomoTracker">
          <input
            type="checkbox"
            id="matomo-opt-out"
            v-model="matomoCheckboxValue"
            @click="toggleOptOut"
          />
          <label for="matomo-opt-out" style="margin-left: 1em"
            ><strong>{{ matomoOptOutLabel }}</strong></label
          >
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="privacy-policy-changes"
        title="Changes to this privacy policy"
      >
        <p>
          We may update this Privacy Policy. Any changes will be posted on this
          page, and we will update the "Last Updated" date of this policy.
        </p>
      </StaticSectionAtom>

      <br />

      <p><strong>Last updated:</strong> <i>2026-11-12</i></p>
    </template>
  </StaticContentComponent>
</template>
