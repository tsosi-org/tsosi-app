<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
</script>

<template>
  <StaticContentComponent title="Legal notice">
    <template #default>
      <StaticSectionAtom id="data-content-policy" title="Data & content policy">
        <ol>
          <li>
            TSOSI data includes information on financial transfers made to
            support open science infrastructure.
          </li>
          <li>
            The content of the TSOSI website includes the text present on all
            the pages of the site.
          </li>
          <li>
            Unless otherwise stated, both the data and the content are licensed
            with a
            <ExternalLinkAtom
              :href="'https://creativecommons.org/licenses/by-sa/4.0/'"
              :label="'CC BY-SA 4.0 license'"
            />. Collecting, using, and reusing part or all of this data and
            content must be done in accordance under the terms of the CC BY-SA
            license.
          </li>
        </ol>
      </StaticSectionAtom>

      <StaticSectionAtom id="copyright" title="Copyright">
        <p>
          Copyright of this website and the intellectual property contained
          herein is owned by Université Grenoble Alpes, 621 Avenue Centrale,
          38400 Saint-Martin-d'Hères, France. All defaults to all rights
          reserved unless otherwise specified.
          <RouterLink :to="'/pages/faq#contact-us'">Contact TSOSI</RouterLink>.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="disclaimer" title="Disclaimer">
        <p>
          The Université Grenoble Alpes cannot, in any way, be held liable for
          the content of the information found on this website or for any
          consequences that may result from its use or interpretation.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="hyperlinks" title="Hypertext links">
        <p>
          The establishment of hypertext links by third parties to pages or
          documents distributed on this site is authorized, provided that the
          links do not contravene the interests of the Université Grenoble
          Alpes, and that they allow users to identify the origin and author of
          the document.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="personal-data-protection"
        title="Protection of personal data"
      >
        <p>
          Information on personal data protection for this site is available on
          the
          <RouterLink to="/pages/privacy-policy/"
            >Privacy policy page</RouterLink
          >.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="publication-director" title="Publication Director">
        <p>Yassine Lakhnech, President of the University of Grenoble Alpes.</p>
      </StaticSectionAtom>

      <StaticSectionAtom id="web-host" title="Web host">
        <p>
          Université Grenoble Alpes
          <br />
          Direction générale déléguée au Système d'information
          <br />
          41 rue des mathématiques, 38610 Gières, France
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="project-host" title="Project host">
        <p>
          The project is hosted by GRICAD, Grenoble Alps Research Scientific
          Computing and Data Infrastructure,
          <ExternalLinkAtom
            :label="'gricad.univ-grenoble-alpes.fr'"
            :href="'https://gricad.univ-grenoble-alpes.fr'"
          />.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="credits" title="Credits">
        <ul>
          <li>Project leader: Maxence Larrieu</li>
          <li>Data and web engineer: Guillaume Alzieu</li>
          <li>Logo: Gilles Esparbet</li>
        </ul>
      </StaticSectionAtom>
    </template>
  </StaticContentComponent>
</template>
