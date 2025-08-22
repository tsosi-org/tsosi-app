<script setup lang="ts">
import { RouterLink } from "vue-router"

import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Frequently Asked Questions">
    <template #default>
      <StaticSectionAtom
       id="tsosi-meaning"
       title="What does TSOSI mean?"
      >
      <p>
        TSOSI stands for
        <b>Transparency to sustain open science infrastructure</b>.
      </p>
      </StaticSectionAtom>
      <StaticSectionAtom
        id="beta-version"
        title="What are the implications of the beta version?"
      >
        <ul>
          <li>
            Data scope: The TSOSI platform includes data from 5 infrastructures:
            DOAJ, DOAB, PCI, SciPost, and OPERAS. This is already relevant,
            because it's the first time that one can explore these data, but
            keep in mind that it's only a small part of the funding landscape
            for open science.
          </li>

          <li>
            DOAB and DOAJ date range: The data starts from 2021. Therefore, all
            financial supports made before 2021 will not appear in TSOSI.
          </li>

          <li>
            The data of TSOSI are mostly produced manually. The name of the supporters' organization received by TSOSI is handwritten, and the identifiers are added 
            semi manually by the TSOSI operational team. Therefore, the TSOSI data may contain errors. Please <RouterLink :to="'#contact-us'">Contact us</RouterLink> 
            if you think you have found one.
          </li>
          
          <li>
            TSOSI's URL: the weblinks of the entities contain identifiers.
            <br />
            By default, the URL is formed with the entity's ROR identifier to
            provide a persistent URL,
            <i>e.g.</i>
            
            <CodeBlockAtom
              :content="'https://tsosi.org/entities/02rx3b187'"
              :inline="true"
              :background="true"
            /> for <RouterLink :to="{ name: 'entity', params: { id: '02rx3b187' }}" >Université Grenoble Alpes</RouterLink>.

            <br />
            If no ROR identifier is known, a random unique identifier is
            generated, 
            <i>e.g.</i>

            <CodeBlockAtom
              :content="'https://tsosi.org/entities/e5f5f1d5-cd16-48c5-94d9-f73ce7968195'"
              :inline="true"
              :background="true"
            />, which will not be persistent. Each time TSOSI ingests new data,
            this URL may change. Therefore, if you would like to share
            the webpage of a TSOSI's organization without known ROR identifier,
            it's best to also share its
            full name.
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
        id="data-provider-infra"
        title="What are the infrastructures that provide the data?"
      >
        <p>
          The financial data comes from TSOSI partners' infrastructures: DOAJ,
          DOAB, SciPost, PeerCommunityIn, and OPERAS.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="join-tsosi" title="How can I join TSOSI?">
        <p>
          <b>Infrastructure</b>: We'd love to include new infrastructure!
          <RouterLink :to="'#contact-us'">Contact us</RouterLink>. You will need
          to provide (i) financial data structured in accordance with the
          <ExternalLinkAtom
            :label="'data collection schema'"
            :href="'https://github.com/tsosi-org/data-collection-schema'"
          />
          and (ii) the Memorandum of Understanding signed by both the
          infrastructure's legal entity and Université Grenoble Alpes.
          <br />
          <br />

          <b>Institutions and consortia</b>: TSOSI also strongly welcomes
          institutions and consortia to join the project. For the 2025-26 cycle,
          we plan to work with consortia to collect and ingest these new data.
          For research institutions, we plan to work with
          <ExternalLinkAtom
            :label="'openCost'"
            :href="'https://www.opencost.de/en/'"
          />, which allows institutions to notably practise open data for
          funding made in favor of open infrastructures:
          <RouterLink :to="'#contact-us'">drop us a line</RouterLink>
          to be part of this!
        </p>
      </StaticSectionAtom>

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
          No. For its launching year, TSOSI has worked with infrastructures more
          focused on publications, but all infrastructures, like the one
          dedicated to software, data, monitoring, or identifiers, are, of
          course, in the scope of TSOSI.
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
        id="data-sources"
        title="What are the data sources of TSOSI?"
      >
        <p>
          Financial data comes from
          <RouterLink :to="'#data-provider-infra'"
            >partner infrastructures</RouterLink
          >
          and organization metadata from the
          <ExternalLinkAtom
            :label="'Research Organization Registry'"
            :href="'https://ror.org'"
          />
          (ROR) and
          <ExternalLinkAtom
            :label="'Wikidata'"
            :href="'https://www.wikidata.org'"
          />.

          <i>Financial data</i> are sent by the partner infrastructures and
          enriched semi-manually with ROR and Wikidata identifiers by the TSOSI
          operational team. Thanks to these identifiers, TSOSI software collects
          <i>organization metadata</i>: name, alias, country, inception date,
          and geographic location come from ROR and Wikidata. The short
          paragraph describing the organization is collected from Wikipedia,
          while the logo comes from Wikimedia Commons.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="data-update-frequency"
        title="With which frequency is the data updated?"
      >
        <p>
          It depends on the infrastructure. The lowest frequency at which the
          data are updated is once a year; the maximum frequency could be once a
          day.
          
          For example, the SciPost financial data are updated once a week thanks
          to its software, which includes an API, see the
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
          see how to use with this
          <ExternalLinkAtom
            :label="'API use case'"
            :href="'https://github.com/tsosi-org/api-use-cases'"
          />
          repository. The data dump is pending. Please be patient; we still need
          to work on the quality.
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
        id="why-dont-i-see-the-supports-made-by-my-organization"
        title="Why don't I see the supports made by my organization?"
      >
        <p>
          TSOSI is in beta version: for its launch, it includes only the
          financial support made by
          <RouterLink :to="'#data-provider-infra'"
            >partner infrastructures</RouterLink
          >. Moreover, note that the data from DOAB and DOAJ begin in 2021, so
          users will not find the financial data made before this year.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="doaj-or-doab-page-missing-institution"
        title="From the DOAJ or DOAB page, why can I not see my institution?"
      >
        <p>
          First, note that TSOSI has DOAJ and DOAB financial data starting in
          2021. It's indicated in TSOSI's platform in the middle of their
          webpage. Secondly, and only for the DOAJ, note that for 2021, TSOSI
          did not have the breakdown data, but only the intermediary one, like a
          library consortium. These two factors can explain why you don't see
          your institution's contribution.
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
        id="amounts-hidden"
        title="Why are the support amounts hidden sometimes?"
      >
        <p>
          Partner infrastructures have the choice to display or not the amount
          of the financial support. TSOSI is new, its data are new, and
          therefore some infrastructure has made the choice to hide the amount.
        </p>
      </StaticSectionAtom>
      
      <StaticSectionAtom
        id="organization-names"
        title="How are multilingual organization names handled?"
      >
        <p>
          The name of the organization comes, in order of priority:
        </p>
        <ul>
          <li>
            from the attached ROR record: we use the preferred label as
            it appears on the record page.
          </li>
          <li>
            from the attached Wikidata item: we use the English label from
            the item and fall back to the default label.
          </li>
        </ul>
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
            Settlements's</ExternalLinkAtom
          >
          (the service provides daily rates). We then compute the rate to be
          used for each transfer, depending on the accuracy of the transfer
          date:
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
        id="add-data-from-my-institution"
        title="How can I add the support made by my institution?"
      >
        <p>
          For its next cycle, 2025-26, TSOSI is keen to include other data
          sources! For research institution, the idea is to work with 
          <ExternalLinkAtom
            :label="'openCost'"
            :href="'https://www.opencost.de/en/'"
          />, which allows institutions to notably practise open data for funding made 
          in favor of open infrastructures: <RouterLink :to="'#contact-us'">Drop us a line</RouterLink> to be part of this!
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="entities-hierarchies"
        title="Does TSOSI include relationships and hierarchies?"
      >
        <p>
          In this beta version, the supporters are not linked between them, and
          no relationship between them is implemented. It is something that can
          be added using the
          <ExternalLinkAtom
            :label="'relationship metadata from the ROR data schema'"
            :href="'https://ror.org/about/faqs/#does-ror-support-relationships-and-hierarchies'"
          />, for example. Feel free to vote for this feature inside our
          <ExternalLinkAtom
            :label="'roadmap'"
            :href="'https://github.com/orgs/tsosi-org/projects/2'"
          />.
        </p>
      </StaticSectionAtom>

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
