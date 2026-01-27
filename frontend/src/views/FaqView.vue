<script setup lang="ts">
import { RouterLink } from "vue-router"

import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import { getPartners, type Entity } from "@/singletons/ref-data"
import { shuffleArray } from "@/utils/data-utils"
import StaticContentComponent from "@/views/StaticContentView.vue"

const partners = getPartners() as Entity[]
shuffleArray(partners)

function formatPartners(partners: Entity[]): String {
  const arr = partners.map((p) => p?.short_name || p.name)
  return arr.slice(0, -1).join(", ") + " and " + arr.slice(-1)
}
</script>

<template>
  <StaticContentComponent title="Frequently Asked Questions">
    <template #default>
      <StaticSectionAtom
        id="beta-version"
        title="What are the implications of the beta version?"
      >
        <ul>
          <li>
            Data scope: The TSOSI platform includes data solely from
            <RouterLink to="#data-provider">its providers</RouterLink>. This is
            already relevant, because it's the first time that one can explore
            these data, but keep in mind that it's only a small part of the
            funding landscape for open infrastructures.
          </li>

          <li>
            DOAB and DOAJ date range: The data starts from 2021. Therefore, all
            financial supports made before 2021 will not appear in TSOSI.
          </li>

          <li>
            TSOSI’s data are mostly produced manually. The name of supporting
            organizations received by TSOSI is handwritten, and the identifiers
            are added semi-manually by the TSOSI operational team. Therefore,
            the TSOSI data may contain errors. Please
            <RouterLink :to="'#contact-us'">contact us</RouterLink>
            if you think you have found one.
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="project-history"
        title="What is the project's history?"
      >
        <p>
          TSOSI officially started in September 2024, funded by the
          <ExternalLinkAtom
            :label="'French Committee for Open Science'"
            :href="'https://www.ouvrirlascience.fr/home/'"
          />, with the commitment of
          <ExternalLinkAtom
            :label="'Université Grenoble Alpes'"
            :href="'https://www.univ-grenoble-alpes.fr/english/'"
          />
          to lead the project. The idea of the platform originated in 2020
          within a research library: if everyone can see which organizations
          have financially supported an open infrastructure, then the decision
          to do the same would become much more evident.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="who-runs-tsosi" title="Who runs TSOSI?">
        <p>
          Université Grenoble Alpes leads the project, and the French Committee
          for Open Science is the funder. SCOSS, DOAJ, DOAB, SciPost,
          PeerCommunityIn, OPERAS, and Couperin are part of the governance of
          the project.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="tsosi-meaning" title="What does TSOSI mean?">
        <p>
          TSOSI stands for
          <b>Transparency to sustain open science infrastructure</b>.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="pronounce-tsosi"
        title="How do you pronounce TSOSI?"
      >
        <p>
          It's like the beginning of the word “society” with a “t” at the
          beginning: “t-sosci”.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="data-provider"
        title="Where does the financial data come from?"
      >
        <p>So far, the providers are: {{ formatPartners(partners) }}.</p>
      </StaticSectionAtom>

      <StaticSectionAtom id="join-tsosi" title="How can I join TSOSI?">
        <p>
          We are eager to welcome your institution or infrastructure within
          TSOSI.org. We believe that the more data we have about financial
          support for open infrastructures, the more supporters we will attract.
          Please see our
          <ExternalLinkAtom
            :label="'data collection schema'"
            :href="'https://github.com/tsosi-org/data-collection-schema'"
          />
          on Github to review the data needed, and
          <RouterLink :to="'#contact-us'">contact us</RouterLink> to be part of
          this exciting initiative.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="why-dont-i-see-the-supports-made-by-my-organization"
        title="Why don't I see the supports made by my organization?"
      >
        <p>
          TSOSI's data only comes from
          <RouterLink :to="'#data-provider'">its providers</RouterLink>. You are
          very welcome to be part of this, so that all your support can be
          included.
          <br />
          See <RouterLink :to="'#join-tsosi'">How can I join TSOSI?</RouterLink>
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="doaj-or-doab-page-missing-institution"
        title="From the DOAJ or DOAB page, why can I not see my institution?"
      >
        <p>
          First, note that TSOSI has DOAJ and DOAB financial data starting in
          2021. This is indicated on the TSOSI platform, in the middle of their
          webpage. Secondly, and only for the DOAJ, note that for 2021, TSOSI
          did not have the breakdown data, but only intermediary entities, such
          as library consortium. These two factors can explain why you don't see
          your institution's contribution.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="contact-us" title="How to contact TSOSI?">
        <p>
          Any support and feedback are strongly welcome, reach us at
          <CodeBlockAtom
            :content="'contact (the at symbol) tsosi.org'"
            :inline="true"
            :background="true"
          />.
        </p>
      </StaticSectionAtom>

      <!-- SCOPE AND DEFINITION -->

      <StaticSectionAtom
        id="open-science-infrastructure-meaning"
        title="What do you mean by open science infrastructure?"
      >
        <p>
          Open Science combines various movements and practices aiming to make
          multilingual science knowledge openly available. Open science
          infrastructure encompasses software, standards, protocols, services,
          platforms, and organizations that allow scholarly stakeholders to
          practise, develop, think about, and observe open science.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="tsosi-publications-infrastructure"
        title="Does TSOSI only concern infrastructures dedicated to publications?"
      >
        <p>
          No. In its launch year, TSOSI has worked with infrastructures more
          focused on publications, but all infrastructures, like the one
          dedicated to software, data, monitoring, or identifiers, are, of
          course, in the scope of TSOSI.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="contracts-or-transfers"
        title="Is TSOSI more related to contracts or transfers between stakeholders?"
      >
        <p>
          Two levels can be used to describe support between an organization and
          an infrastructure. The first is the administrative level, which
          relates to contracts, agreements, subscriptions, or programs. It
          covers the type of agreement and the terms or conditions involved. The
          second is the financial level, which includes the date of the
          financial transfer, the sender and recipient, and the amount
          transferred. For its launch, TSOSI focuses solely on the financial
          level. Therefore, it does not display information such as the duration
          of the contracts.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="how-does-tsosi-manage-its-url"
        title="How does TSOSI manage its URLs?"
      >
        <p>
          All entities of TSOSI have a unique URL. If an entity has a ROR
          identifier, it is included in its URL, <i>e.g.</i>

          <CodeBlockAtom
            :content="'https://tsosi.org/entities/02rx3b187'"
            :inline="true"
            :background="true"
          />. If not, an internal identifier is generated instead, <i>e.g.</i>
          <CodeBlockAtom
            :content="'https://tsosi.org/entities/e5f5f1d5-cd16-48c5-94d9-f73ce7968195'"
            :inline="true"
            :background="true"
          />.<br />

          Note that <b>only the URLs with the ROR identifier are persistent</b>.
          The others may change each time TSOSI ingests new data. If you find a
          missing ROR for an institution, please
          <RouterLink :to="'#contact-us'">contact us</RouterLink>.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="data-update-frequency"
        title="With which frequency is the data updated?"
      >
        <p>
          It depends on the source of data. The lowest frequency at which the
          data are updated is once a year; the maximum frequency could be once a
          day. For example, the SciPost financial data are updated once a week
          thanks to its software, which includes an API, see the
          <ExternalLinkAtom
            :label="'subsidies page on scipost.org'"
            :href="'https://scipost.org/finances/subsidies/'"
          />.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="data-access" title="How can I access the data?">
        <p>
          Below each table and graph, you can find an
          <CodeBlockAtom
            :content="'export button'"
            :inline="true"
            :background="true"
          />, which allows you to get the data. Moreover, we have an open API:
          see how to use it in this
          <ExternalLinkAtom
            :label="'API use-case'"
            :href="'https://github.com/tsosi-org/api-use-cases'"
          />
          repository.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="data-license"
        title="What license is applied to the data?"
      >
        <p>
          Re-use of TSOSI's data is highly encouraged! Data is shared under a
          CC-BY-SA license. Just cite tsosi.org and apply the same license — see
          our
          <RouterLink :label="''" :to="'/pages/legal-notice'"
            >Legal notice page</RouterLink
          >
          fore more details. We'd love to hear about how you're using the data,
          so feel free to
          <RouterLink :label="''" :to="'#contact-us'">let us know</RouterLink>!
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="what-does-the-date-column-refer-to"
        title="What does the date column refer to?"
      >
        <p>
          The date field is relative: it can show either when the transfer was
          made or when it was received. Therefore, when a support is made by a
          consortium on behalf of an institution, it's the date of the transfer
          to the infrastructure that is shown. Note also that the date accuracy
          may vary according to the data TSOSI received: for its launching,
          TSOSI has mainly a yearly accuracy, and sometimes a monthly or even
          daily accuracy.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="logos-and-descriptions"
        title="How does TSOSI get logos and descriptions?"
      >
        <p>
          Logos and descriptions come from Wikipedia and Wikimedia Commons. We
          retrieve them using Research Organization Registry (ROR) and Wikidata
          identifiers. These identifiers are added semi-automatically to the
          collected data. Is your logo or description missing?
          <RouterLink :to="'#add-logo'">See how to solve that</RouterLink>.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="amounts-hidden"
        title="Why are the support amounts hidden sometimes?"
      >
        <p>
          Partner infrastructures have the choice to display or not the amount
          of the financial support. TSOSI is new, its data are new, and
          therefore some infrastructures have chosen to hide the amount.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="currency-change"
        title="How is the currency change managed?"
      >
        <p>
          We provide converted amounts for the currencies involved in one of our
          registered transfers. The amounts are calculated using
          <ExternalLinkAtom :href="'https://data.bis.org/topics/XRU'">
            bilateral exchange rates from the Bank for International
            Settlements</ExternalLinkAtom
          >
          (which provides daily rates). We then compute the rate to be used for
          each transfer, depending on the accuracy of the transfer date:
        </p>
        <ul>
          <li>Daily accuracy: exact daily rate</li>
          <li>
            Monthly or Yearly accuracy: average rate over the given month or
            year
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="organization-names"
        title="How are multilingual organization names handled?"
      >
        <p>The name of the organization comes, in order of priority:</p>
        <ul>
          <li>
            from the attached ROR record: we use the preferred label as it
            appears on the record page.
          </li>
          <li>
            from the attached Wikidata item: we use the English label if there's
            one, otherwise we use the default label.
          </li>
        </ul>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="entities-hierarchies"
        title="Does TSOSI include relationships and hierarchies within an organization?"
      >
        <p>
          TSOSI relies on the
          <ExternalLinkAtom href="https://ror.org/"
            >ROR registry</ExternalLinkAtom
          >. It includes only the parent-child organizational hierarchies that
          are recorded in the registry (see the
          <ExternalLinkAtom
            href="https://ror.org/about/faqs/#does-ror-support-relationships-and-hierarchies"
            >ROR FAQ on relationsphips</ExternalLinkAtom
          >). This means that when support is provided by a child entity, it is
          also displayed under the parent organization. For example, this is the
          case with the
          <RouterLink to="/entities/04dkp9463"
            >University of Amsterdam</RouterLink
          >.
        </p>
      </StaticSectionAtom>

      <!-- ENRICHMENT BY THE USER -->
      <StaticSectionAtom
        id="add-logo"
        title="How can I add the logo of my organization?"
      >
        <p>
          Very good idea! You will need a Wikidata record of your organization
          and your logo file. Here is the process:
        </p>
        <ol>
          <li>
            Add your logo to Wikimedia Commons. Here is an example:
            <ExternalLinkAtom
              :label="'https://commons.wikimedia.org/wiki/File:Logo_Universit%C3%A9_Grenoble_Alpes_2020.svg'"
              :href="'https://commons.wikimedia.org/wiki/File:Logo_Universit%C3%A9_Grenoble_Alpes_2020.svg'"
            />
          </li>

          <li>
            Go to the Wikidata record of your institution and click on "add
            statement"
          </li>

          <li>Add the following property: "logo image" (P154)</li>

          <li>
            In the new field, copy-paste the title of the file you have uploaded
            inside Wikimedia Commons, <i>e.g.</i>
            <CodeBlockAtom
              :content="'File:Logo_Université_Grenoble-Alpes_(2020).jpg'"
              :inline="true"
              :background="true"
            />
          </li>

          <li>That's it! Your logo will be included in TSOSI in 24 hours</li>
        </ol>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="add-wiki-description"
        title="How can I add a description of my organization?"
      >
        <p>
          You will need both a Wikidata record and a Wikipedia entry for your
          organization. Here is the process:
        </p>
        <ol>
          <li>
            Enrich or create the Wikipedia entry of your organization in
            English.
          </li>

          <li>
            At the very bottom of the Wikidata record of your organization, add
            the latter Wikipedia entry inside the Wikipedia box, <i>e.g.</i>
            <ExternalLinkAtom
              :label="'https://www.wikidata.org/wiki/Q945876'"
              :href="'https://www.wikidata.org/wiki/Q945876'"
              class="wikidata-inline-link"
            />.
          </li>

          <li>
            That's it! The description will be included in TSOSI in 24 hours.
          </li>
        </ol>
      </StaticSectionAtom>
    </template>
  </StaticContentComponent>
</template>
