<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="FAQ">
    <template #default>
      <h2 id="osi-definition">
        How do you define open science infrastructure?
      </h2>
      <p>
        Open Science combines various movements and practices aiming to make
        multilingual science knowledge openly available. Open science
        infrastructure encompasses softwares, standards, protocols, services,
        platforms that allow scholarly stakeholders to practise, develop and
        observe open science.
      </p>

      <h2 id="tsosi-focus">
        Is the project focused on open science infrastructure for publication in
        particular (open access)?
      </h2>
      <p>
        No, TSOSI aims to include all infrastructures that support open science.
        We can think of the three main scientific outputs: software, data and
        publication; TSOSI aims to include infrastructure that helps make these
        artefacts openly available.
      </p>

      <h2 id="partner-definition">
        How would you define if an infrastructure can join or not the project?
      </h2>
      <p>
        A list of criteria is currently (2024-10) being defined. It will help in
        the decision-making process when it comes to integrating an
        infrastructure. To set the criteria we will start with the one from
        SCOSS (see the 2024 Expression of Interest and the FAQ).
      </p>

      <h2 id="country-focus">
        Is the project focused on French open science infrastructure?
      </h2>
      <p>
        No. The funder, for the launching year, is the French Committee for Open
        Science, but TSOSI has an international scope.
      </p>

      <h2 id="commercial-inclusion">
        Does the project exclude infrastructures that commercialise services?
      </h2>
      <p>
        No. Infrastructure can sell services, but should not sell data: “data
        related to the running of the scholarly infrastructure should be
        community property. Appropriate revenue sources might include
        value-added services, consulting, API Service Level Agreements or
        membership fees” (cf. The Principles of Open Scholarly Infrastructure)
      </p>

      <h2 id="osi-scale">
        Is the project solely dedicated to large-scale open science
        infrastructure?
      </h2>
      <p>
        No, we also include smaller infrastructures, such as publishing
        platforms at national or regional level. For example
        <a
          href="https://peercommunityin.org/"
          target="_blank"
          rel="noopener noreferrer"
        >
          PeerCommunityIn
        </a>
        and
        <a href="https://scipost.org" target="_blank" rel="noopener noreferrer">
          SciPost
        </a>
        are partners of the project.
      </p>
    </template>
  </StaticContentComponent>
</template>
