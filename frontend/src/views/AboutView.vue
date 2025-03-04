<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="About">
    <template #default>
      <p>
        Transparency to Sustain Open Science Infrastructure is a project funded
        by the French Committee for open science, that is the political body
        dedicated to open science within the French ministry of research &
        education. The project is leaded by Université Grenoble Alpes and the
        following infrastructure are partners: OPERAS, DOAJ, DOAB, Couperin,
        SciPost, PeerCommuntyIn, SCOSS, Couperin. The very goal of the project
        is to contribute to the sustainability of the open science
        infrastructure. How? TSOSI will enhance the value of entities that has
        fund open science infrasutrcture. A website will be make (planned for
        June 2025) that will show the funding received by our partner's
        infrastructure: DOAJ, DOAB, SciPost, OPERAS and PeerCommunityIn.
      </p>

      <h2>Governance</h2>
      <ul>
        <li>
          Supervision team : French Committee for open science, Université
          Grenoble Alpes
        </li>
        <li>
          Operationnal team : Maxence Larrieu, Guillaume Alzieu, Joanna Janik,
          as members of the GRICAD unit
        </li>
        <li>Advisory board: SCOSS, OPERAS, DOAB, DOAJ</li>
        <li>User Group: Couperin, PeerCommunityIn, SciPost</li>
      </ul>

      <h2>Contact</h2>
      <p>
        For any question feel free to reach us at
        <kbd>contact[the famous symbol]tsosi.org</kbd>
      </p>

      <h2>License</h2>
      <p>
        Unless otherwise noted, all content on this site is released under a
        <a
          href="https://creativecommons.org/licenses/by-sa/4.0/deed.en"
          target="_blank"
          rel="noopener noreferrer"
        >
          Creative Commons Attribution 4.0 International License
        </a>
        .
      </p>
    </template>
  </StaticContentComponent>
</template>
