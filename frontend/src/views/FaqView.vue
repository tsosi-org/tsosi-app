<script setup lang="ts">
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="FAQ">
    <template #default>
      
      <!-- some notes for Guillaume: 
      - I have used InternalLinkAtom and also <ol> for numbered list
      - Add your entry "How is the currency change managed?" after the entry "Why are the support amounts sometimes hidden?"
      -->

      <h2 id="beta-version">What’s the implication of the beta version?</h2>
      <ul>
        <li>Data scope: The TSOSI platform includes data from 5 infrastructures: DOAJ, DOAB, PCI, SciPost, and OPERAS. This is already relevant, because it’s the first time that one can explore these data, but keep in mind that it’s only a small part of the funding landscape for open science. </li>

        <li>DOAB and DOAJ date range: The data starts from 2021. Therefore, all supports made before 2021 will not appear in TSOSI</li>

        <li>Two levels can be used to describe support between an organization and an infrastructure. The first is the administrative level, which relates to agreements, subscriptions, contracts, or programs. It covers the type of agreement and the terms or conditions involved. The second is the financial level, which includes the date of the financial transfer, the sender and recipient, and the amount transferred. For its initial launch, TSOSI focuses solely on the financial level. Therefore, it does not display information such as the duration of the subscriptions.

        <li>URL of the entities: the weblink to the entities contains identifiers, <i>e.g.</i>, 
        <CodeBlockAtom
          :content="'tsosi.org/entities/e5f5f1d5-cd16-48c5-94d9-f73ce7968195'"
          :inline="true"
          :background="true"
        />, which are not persistent. Each time TSOSI ingests new data, this URL changes. Therefore, if you would like to share the webpage of a TSOSI’s organization, it’s best to share also its full name.</li>
      </ul>      
      
      <h2 id="project-history">What is the project’s history?</h2>
      <p>
        TSOSI officially started in September 2024, funded by the
        <ExternalLinkAtom
          :label="'French Committee for Open Science'"
          :href="'https://www.ouvrirlascience.fr/home/'"
        />, with the commitment of 
        <ExternalLinkAtom
          :label="'Université Grenoble Alpes'"
          :href="'https://www.univ-grenoble-alpes.fr/english/'"
        /> to lead the project. The idea of the platform originated in 2020 within a research library: if everyone can see which organizations have financially supported an open infrastructure, then the decision to do the same would become much more evident.
      </p>

      <h2 id="who-runs-tsosi">Who runs TSOSI?</h2>
      <p>
      Université Grenoble Alpes leads the project, and the French Committee for Open Science is the funder. 
      SCOSS, DOAJ, DOAB, SciPost, PeerCommunityIn, OPERAS, and Couperin are part of the governance of the project.
      </p>

      <h2 id="pronounce-tsosi">How do you pronounce TSOSI?</h2>
      <p>
      It’s like the beginning of the word “society” with a “t” at the beginning: “t-sosci”.
      </p>

      <h2 id="data-provider-infra">What are the infrastructures that provide the data?</h2>
      <p>
      The financial data comes from TSOSI partners' infrastructures: DOAJ, DOAB, SciPost, PeerCommunityIn, and OPERAS.
      </p>

      <h2 id="join-tsosi">How can I join TSOSI?</h2>
      <p>
      <b>Infrastructure</b>: We’d love to include new infrastructure! 
      <InternalLinkAtom
        :label="'Contact us'"
        :href="'/faq#contact-us'"
      />. You will need to provide (i) financial data structured in accordance with the 
        <ExternalLinkAtom
          :label="'data collection schema'"
          :href="'https://github.com/tsosi-org/data-collection-schema'"
        /> and (ii) the Memorandum of Understanding signed by both the infrastructure’s legal entity and Université Grenoble Alpes. <br /> <br/>

       <b>Institutions and consortia</b>: TSOSI also strongly welcomes institutions and consortia to join the project. For the 2025-26 cycle, we plan to work with consortia to collect and ingest these new data. For research institutions, we plan to work with 
        <ExternalLinkAtom
          :label="'openCost'"
          :href="'https://www.opencost.de/en/'"
        />, which allows institutions to notably practise open data for funding made in favor of open infrastructures: 
        <InternalLinkAtom
          :label="'drop us a line'"
          :href="'/faq#contact-us'"
        /> to be part of this! 
      </p>

      <h2 id="open-science-infrastructure-meaning">What do you mean by open science infrastructure?</h2>
      <p>
        Open Science combines various movements and practices aiming to make multilingual science knowledge openly available. Open science infrastructure encompasses software, standards, protocols, services, platforms, and organizations that allow scholarly stakeholders to practise, develop, think about, and observe open science.
      </p>

      <h2 id="tsosi-publications-infrastructure">Does TSOSI only concern infrastructures dedicated to publications?</h2>
      <p>
        No. For its launching year, TSOSI has worked with infrastructures more focused on publications, but all infrastructures, like the one dedicated to software, data, monitoring, or identifiers, are, of course, in the scope of TSOSI.
      </p>

      <h2 id="contact-us">How to contact TSOSI?</h2>
      <p>
        Any support and feedback are strongly welcome, reach us at
        <CodeBlockAtom
          :content="'contact (the at symbol) tsosi.org'"
          :inline="true"
          :background="true"
        />.
      </p>

      <h2 id="data-sources">What are the data sources of TSOSI?</h2>
      <p>
        Financial data comes from 
        <InternalLinkAtom
          :label="'partner infrastructures'"
          :href="'/faq#data-provider-infra'"
        /> and organizational metadata from the 
        <ExternalLinkAtom
          :label="'Research Organization Registry'"
          :href="'https://ror.org'"
        /> (ROR) and
        <ExternalLinkAtom
          :label="'Wikidata'"
          :href="'https://www.wikidata.org'"
        />.

        <i>Financial data</i> are sent by the partner infrastructures and enriched semi-manually with ROR and Wikidata identifiers by the TSOSI operational team. Thanks to these identifiers, TSOSI software collects <i>organisational metadata</i>: name, alias, country, inception date, and geographic location come from ROR and Wikidata. The short paragraph describing the organization is collected from Wikipedia, while the logo comes from Wikimedia Commons.
      </p>
    
      <h2 id="data-update-frequency">With which frequency is the data updated?</h2>
      <p>
        It depends on the infrastructure. The lowest frequency at which the data are updated is once a year; the maximum frequency is once a day. For example, the SciPost financial data are updated once a day thanks to its software, which includes an API, see the
        <ExternalLinkAtom
          :label="'organization \'s page on scipost.org'"
          :href="'https://scipost.org/organizations/'"
        />.
      </p>

      <h2 id="data-access">How can I access the data?</h2>
      <p>
        Below each table and graph, you can find an
        <CodeBlockAtom
          :content="'export button'"
          :inline="true"
          :background="true"
        />, which allows you to get the data. Moreover, we have an open API: see how to use with this 
        <ExternalLinkAtom
          :label="'API use case'"
          :href="'https://github.com/tsosi-org/api-use-cases'"
        /> repository. The data dump is pending. Please be patient; we still need to work on the quality.
      </p>

      <h2 id="data-license">What license is applied to the data?</h2>
      <p>
       CC-BY-SA license: You must cite tsosi.org and apply the same license, see the
        <InternalLinkAtom
          :label="'Legal notice page'"
          :href="'/legal-notice'"
        />. Please 
        <InternalLinkAtom
          :label="'inform us'"
          :href="'/faq#contact-us'"
        />. We'd love to be aware of any re-use.
      </p>

      <h2 id="why-dont-i-see-the-supports-made-by-my-organization">Why don’t I see the supports made by my organization?</h2>
      <p>
        TSOSI is in beta version: for its launch, it includes only the financial support made by 
        <InternalLinkAtom
          :label="'partner infrastructures'"
          :href="'/faq#data-provider-infra'"
         />. Moreover, note that the data from DOAB and DOAJ begin in 2021, so users will not find the financial data made before this year.
      </p>

      <h2 id="from-the-doaj-or-doab-page-why-can-i-not-see-my-institution">From the DOAJ or DOAB page, why can I not see my institution?</h2>
      <p>
        First, note that TSOSI has DOAJ and DOAB financial data starting in 2021. It’s indicated in TSOSI’s platform in the middle of their webpage. Secondly, and only for the DOAJ, note that for 2021, TSOSI did not have the breakdown data, but only the intermediary one, like a library consortium. These two factors can explain why you don’t see your institution's contribution.
      </p>

      <h2 id="what-does-the-date-column-refer-to">What does the date column refer to?</h2>
      <p>
        The date field is relative: it can show either when the transfer was made or when it was received. Therefore, when a support is made by a consortium on behalf of an institution, it’s the date of the transfer to the infrastructure that is shown.
      </p>

      <h2 id="amounts-hidden">Why are the support amounts sometimes hidden?</h2>
      <p>
        Partner’s infrastructure has the choice to display or not the amount of the financial support. TSOSI is new, its data are new, and therefore some infrastructure has made the choice, for the moment, to hide the amount.
      </p>

      <h2 id="add-data-from-my-institution">How can I add the support made by my institution?</h2>
      <p>
        For its next cycle, 2025-26, TSOSI is keen to include other data sources! If you represent a research institution, we invite you to practise open data following the guidelines and schema of the 
        <ExternalLinkAtom
          :label="'openCost'"
          :href="'https://www.opencost.de/en/'"
        /> project. TSOSI will then collect your structured and enriched data. Feel free to
        <InternalLinkAtom
          :label="'Contact us'"
          :href="'/faq#contact-us'"
        /> to make that idea real!
      </p>

      <h2 id="entities-hierarchies">Does TSOSI support relationships and hierarchies?</h2>
      <p>
        In this beta version, the supporters are not linked between them, and no relationship between them is implemented. It is something that can be added using the 
        <ExternalLinkAtom
          :label="'relationship metadata from the ROR data schema'"
          :href="'https://ror.org/about/faqs/#does-ror-support-relationships-and-hierarchies'"
        />, for example. Feel free to vote for this feature inside our  
        <ExternalLinkAtom
          :label="'roadmap'"
          :href="'https://github.com/orgs/tsosi-org/projects/2'"
        />.
      </p>

      <h2 id="add-logo">How can I add the logo of my organization?</h2>
      <p>
        Very good idea! You will need a Wikidata record of your organization and your logo file. Here is the process:
        <ol>
          <li>Add your logo to Wikimedia Commons. Here is an example: 
            <ExternalLinkAtom
              :label="'https://commons.wikimedia.org/wiki/File:Logo_Universit%C3%A9_Grenoble_Alpes_2020.svg'"
              :href="'https://commons.wikimedia.org/wiki/File:Logo_Universit%C3%A9_Grenoble_Alpes_2020.svg'"
            /></li>
          
          <li>Go to the Wikidata record of your institution and click on "add statement"</li>

          <li>Add the following property: "logo image" (P154)</li>

          <li>In the new field, copy-paste the title of the file you have uploaded inside Wikimedia Commons, <i>e.g.</i> 
            <CodeBlockAtom
              :content="'File:Logo_Université_Grenoble-Alpes_(2020).jpg'"
              :inline="true"
              :background="true"
            /></li>

          <li>That’s it! Your logo will be included in TSOSI in 24 hours</li>        
        </ol>
      </p>

      <h2 id="add-wiki-description">How can I add a description of my organization?</h2>
      <p>
        You will need both a Wikidata record and a Wikipedia entry for your organization. Here is the process:
        <ol>
          <li>Enrich or create the Wikipedia entry of your organization in English.</li>
          
          <li>At the very bottom of the Wikidata record of your organization, add the latter Wikipedia entry inside the Wikipedia box, <i>e.g.</i> 
             <ExternalLinkAtom
              :label="'https://www.wikidata.org/wiki/Q945876'"
              :href="'https://www.wikidata.org/wiki/Q945876'"
            />.</li>
          
          <li>That’s it! The description will be included in TSOSI in 24 hours.</li>      
        </ol>

      </p>

    </template>
  </StaticContentComponent>
</template>
