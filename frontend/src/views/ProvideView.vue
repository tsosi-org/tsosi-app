<script setup lang="ts">
import Button from "primevue/button"
import Divider from "primevue/divider"
import { RouterLink, useRoute } from "vue-router"

import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"

const route = useRoute()

// Pre-fill the Grist form with the organization name and ROR URL when given
// as query parameters, e.g. from an entity page.
const query = ["name", "ror_url"]
  .map(
    (key) =>
      `${encodeURIComponent(key)}=${encodeURIComponent((route.query[key] as string) || "")}`,
  )
  .join("&")

const gristFormUrl = `https://tsosi.getgrist.com/forms/3nGNWU5Pisa2byXGKbVdRq/32?style=singlePage&themeSyncWithOs=false&${query}`

const calendarUrl = "https://cal.com/blefeuvr/tsosi"
</script>

<template>
  <StaticContentComponent title="Become a TSOSI data provider">
    <template #default>
      <div class="navigation-list">
        <RouterLink to="#why-join">Why join?</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#who-can-join">Who can join?</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#scope">Scope</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#how-it-works">How it works?</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#data-we-need">Required data</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#license">License</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#get-in-touch">Get in touch</RouterLink>
      </div>

      <p class="intro">
        <b>TSOSI data providers</b> are organizations that make their financial
        support to open infrastructures visible through TSOSI. Institutions,
        consortia, funders and infrastructures are all welcome.
      </p>
      <div class="cta">
        <Button as="router-link" to="#get-in-touch" label="Get in touch" />
      </div>

      <StaticSectionAtom id="why-join" title="Why join?">
        <ul>
          <li>
            <b>Make your support visible.</b> Show your commitment to open
            science infrastructure.
          </li>
          <li>
            <b>Encourage others to follow.</b> When everyone can see who
            supports an infrastructure, the decision to do the same becomes much
            more evident.
          </li>
          <li>
            <b>Reuse your own data.</b> Everything is openly available through
            exports and the
            <ExternalLinkAtom
              href="https://github.com/tsosi-org/api-use-cases"
              label="TSOSI API"
            />, ready to use in your own reporting.
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="who-can-join"
        title="Who can become a TSOSI data provider?"
      >
        <p>
          Any organization that makes or receives financial transfers to open
          infrastructures.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="scope" title="Which infrastructures are in scope?">
        <ul>
          <li>
            <b>Infrastructures already in TSOSI</b> are welcome. You can find
            them on the
            <RouterLink to="/explore?role=recipient">explore page</RouterLink>.
          </li>
          <li>
            <b>TSOSI extends its scope continuously.</b> To be included, a new
            infrastructure must meet the TSOSI scope criteria and be approved by
            our curation board.
          </li>
        </ul>
        <p>
          The TSOSI scope criteria are the following. The infrastructure must:
        </p>
        <ul>
          <li>
            have a non-profit status in the country in which it is based, or be
            owned by a public research institution;
          </li>
          <li>have been operational for at least two years;</li>
          <li>
            receive support from several different funders, showing that it
            faces a sustainability challenge;
          </li>
          <li>
            be consistent with open science as defined by the
            <ExternalLinkAtom
              href="https://doi.org/10.54677/MNMH8546"
              label="UNESCO Recommendation on Open Science (2021)"
            />.
          </li>
        </ul>
        <p>TSOSI focuses on infrastructures, not on individual journals.</p>
      </StaticSectionAtom>

      <StaticSectionAtom id="how-it-works" title="How it works?">
        <ol class="steps">
          <li>
            <b>Get in touch.</b> Fill in the
            <RouterLink to="#get-in-touch">form below</RouterLink>. We'll get
            back to you within a few days.
          </li>
          <li>
            <b>Share your data.</b> Institutions receive a pre-filled
            spreadsheet template to complete. Consortia and infrastructures
            submit their data as-is, and TSOSI handles the data processing.
          </li>
          <li>
            <b>We process your data.</b> We match organization names to their
            <ExternalLinkAtom href="https://ror.org" label="ROR" /> and
            <ExternalLinkAtom
              href="https://www.wikidata.org"
              label="Wikidata"
            />
            identifiers. We also match your supports with those already declared
            in TSOSI, so that the same support is
            <RouterLink to="/pages/faq#data-source"
              >never counted twice</RouterLink
            >.
          </li>
          <li>
            <b>You validate.</b> We send you a preview of how your supports will
            appear on TSOSI. You confirm by email that it is correct and that
            you agree to its publication.
          </li>
          <li>
            <b>Your data is published</b> openly on tsosi.org under a
            <RouterLink to="#license">CC license</RouterLink>, and your
            organization becomes a TSOSI data provider.
          </li>
          <li>
            <b>Keep it up to date.</b> You will be invited to update your data
            at least once a year.
          </li>
        </ol>
        <p>Depending on who you are, you share your data differently:</p>
        <ul>
          <li>
            <b>Institutions</b> (universities, research organizations,
            libraries, government bodies...) fill in a spreadsheet template with
            the supports they made.
          </li>
          <li>
            <b>Consortia</b> share the data they already have. An export from
            Consortia Manager is much appreciated.
          </li>
          <li>
            <b>Infrastructures</b> share the data they already have, for example
            a sheet already filled in for
            <ExternalLinkAtom href="https://scoss.org" label="SCOSS" />.
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="data-we-need"
        title="What data is required to describe a support?"
      >
        <p>
          We describe each financial support with the following data: the
          supporting organization, the infrastructure receiving the support, the
          amount, the currency, and the date.
        </p>
        <p>
          If you enjoy technical descriptions as much as we do, we invite you to
          explore the
          <ExternalLinkAtom
            href="https://github.com/tsosi-org/data-collection-schema"
            label="TSOSI data collection schema on GitHub"
          />.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="license" title="License">
        <p>
          The data you share is published on tsosi.org under the
          <ExternalLinkAtom
            href="https://creativecommons.org/licenses/by-sa/4.0/"
            label="CC BY-SA 4.0 license"
          />.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="get-in-touch" title="Get in touch">
        <iframe
          :src="gristFormUrl"
          title="TSOSI data provider contact form"
          height="1450px"
          width="100%"
          frameborder="0"
        >
        </iframe>
      </StaticSectionAtom>
    </template>
  </StaticContentComponent>
</template>

<style scoped>
.navigation-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 5px;
  margin: 0 30px;
  margin-bottom: 40px;
}

.navigation-list a {
  text-decoration: none;
  color: var(--p-primary-800);
  font-weight: bold;
  font-size: 1rem;
}

.navigation-list a:hover {
  color: var(--p-primary-500);
}

.intro {
  text-align: center;
  font-size: 1.4rem;
  padding: 1rem 0;
}

.cta {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;

  & :deep(.p-button),
  & :deep(.p-button:hover) {
    color: white;
    text-decoration: none;
    font-size: 1.15rem;
  }
}

.steps li,
.static-section li {
  margin-bottom: 0.4em;
}
</style>
