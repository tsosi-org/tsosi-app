<script setup lang="ts">
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"
</script>

<template>
  <StaticContentComponent title="About">
    <template #default>
      <p>  <!-- bigger font like a header text, try centered text also--> 
        TSOSI aims to make financial contributions to open science infrastructure the norm. How? By highlighting all the organizations that have supported open science infrastructure. TSOSI highlights these supporters to encourage broader participation in sustaining open science infrastructure.
      </p>

      <h2>How it started</h2>
      <p>
      TSOSI officially launched in September 2024 with funding from the
        <ExternalLinkAtom
          :href="'https://www.ouvrirlascience.fr/home/'"
          :label="'French Committee for Open Science'"
        />. It is led by
        <ExternalLinkAtom
          :href="'https://www.univ-grenoble-alpes.fr/english/'"
          :label="'Université Grenoble Alpes'"
        /> in France.
       The idea originated in 2020 within a research library: if everyone can see which organizations have supported an open infrastructure, then the decision to contribute financially would become much more evident.
      </p>

      <h2>Approach</h2>
      <p>
        Like 
        <ExternalLinkAtom
          :href="'https://scoss.org'"
          :label="'SCOSS'"
        />, TSOSI shares the same goal: to improve the sustainability of open science infrastructure. To make worldwide research a common good, research needs infrastructure that allows research stakeholders to practice open science. The original approach of TSOSI relies on its data-driven approach. TSOSI disseminates data that represents choices that are coherent with the values of open science. When an organisation financially supports an infrastructure, it produces data, at least: the funder, the beneficiary, the date, and the amount of the support. TSOSI collects, enriches, and organises these data to give visibility to all those who have financially contributed to open science infrastructure. TSOSI data represent choices made to support open infrastructure: the more we disseminate these data, the more evident the choices made to support open infrastructure will be.
      </p>

      <h2>Governance</h2>
      <p>
        The governance structure consists of an advisory board, a user group, and a supervision group. PeerCommunityIn, SciPost, and Couperin are part of the user group. DOAJ, DOAB, OPERAS, and SCOSS are members of the advisory board. Finally, the French Committee for Open Science and Grenoble Alpes University are members of the supervision group.
      </p>

      <h2>Open data and software</h2>
      <p>
      TSOSI is dedicated to openness; we produce open software and open data. The platform’s software is shared on
        <ExternalLinkAtom
          :href="'https://github.com/tsosi-org'"
          :label="'GitHub'"
        />, and the data is accessible via an API, see how to use it in the
        <ExternalLinkAtom
          :href="'https://github.com/tsosi-org/api-use-cases'"
          :label="'api-use-cases'"
        /> repository.
      </p>

      <h2>Related initiatives</h2>
      <p>
        Concerning TSOSI’s goal, we are delighted to work with     
          <ExternalLinkAtom
            :href="'https://scoss.org'"
            :label="'SCOSS'"
          />, which has organized an annual funding call since 2018 to support three to four infrastructures. TSOSI is also closely aligned with Invest in Open, particularly through the
          <ExternalLinkAtom
            :href="'https://infrafinder.investinopen.org/solutions'"
            :label="'Infra Finder'"
          /> tool. If an infrastructure is within the scope of SCOSS or Infra Finder, this is indicated on its page on the TSOSI platform.
  
        TSOSI is also closely connected to the
        <ExternalLinkAtom
          :href="'https://barcelona-declaration.org/'"
          :label="'Declaration of Barcelona on Open Research Information'"
        />, whose signatories are committed to supporting the sustainability of infrastructure. TSOSI is also related to the
        <ExternalLinkAtom
          :href="'https://openscholarlyinfrastructure.org/'"
          :label="'Principles of Open Scholarly Infrastructure'"
        />, a set of guidelines for the governance and sustainability of open scholarly infrastructure.
  
        For its data-driven approach, TSOSI has been highly inspired by
        <ExternalLinkAtom
          :href="'https://openapc.net/'"
          :label="'OpenAPC'"
        />. Moreover, the initiative
        <ExternalLinkAtom
          :href="'https://www.opencost.de/en/'"
          :label="'openCost'"
        /> started in 2021, which permits research institutions to practise open data about financial contributions for open infrastructure, is highly connected to TSOSI.

        The technical design of the platform has been inspired by the famous work of 
        <ExternalLinkAtom
          :href="'https://openalex.org/'"
          :label="'OpenAlex'"
        />, 
        <ExternalLinkAtom
          :href="'https://open.coki.ac/'"
          :label="'CoCKI open access monitor'"
        />, 
        <ExternalLinkAtom
          :href="'https://openapc.net/'"
          :label="'OpenAPC'"
        />, 
        <ExternalLinkAtom
          :href="'https://www.openaire.eu/'"
          :label="'OpenAire'"
        />, and the
        <ExternalLinkAtom
          :href="'https://frenchopensciencemonitor.esr.gouv.fr/'"
          :label="'French open science monitor'"
        />.      
      </p>

      <h2>Contact</h2>
      <p>
      We welcome your inquiries and feedback. Please contact us at 
        <CodeBlockAtom
        :content="'contact (the at symbol) tsosi.org'"
        :inline="true"
        :background="true"
        />. We look forward to hearing from you.
      </p>

      <h2>Credits</h2>
      <p>
       <ul>
       	<li>Maxence Larrieu is the project leader, 
       		<ExternalLinkAtom
                :href="'https://orcid.org/0000-0002-1834-3007'"
                :label="'https://orcid.org/0000-0002-1834-3007'"
              /> >/li>
          <li>Guillaume Alzieu is the data and web engineer</li>
        </ul>
        Both are based at Grenoble Alpes University, within the 
        <ExternalLinkAtom
                :href="'https://gricad.univ-grenoble-alpes.fr/en/'"
                :label="'GRICAD research unit'"
        />, which operates the TSOSI platform. 
      </p>
      
      <!-- old about page-->
      <!--
      <h2>Governance</h2>
      <ul>
        <li>Advisory board: SCOSS, OPERAS, DOAB, DOAJ</li>
        <li>User Group: Couperin, PeerCommunityIn, SciPost</li>
      </ul>

      <h2>Contact</h2>
      <p>
        For any question feel free to reach us at
        <CodeBlockAtom
          :content="'contact (@tsosi.org)'"
          :inline="true"
          :background="true"
        />
      </p>

      <h2 id="license">License</h2>
      <p>
        Unless otherwise noted, all content on this site is released under a
        <ExternalLinkAtom
          :href="'https://creativecommons.org/licenses/by-sa/4.0/deed.en'"
          :label="'Creative Commons Attribution 4.0 International License'"
        />.
      </p>
     -->

      
    </template>
  </StaticContentComponent>
</template>
