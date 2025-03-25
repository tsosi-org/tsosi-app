<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
import EmailAtom from "@/components/atoms/EmailAtom.vue"
</script>

<template>
  <StaticContentComponent title="Legal notice">
    <template #default>
      <h2>Data & content policy</h2>
      <ol>
        <li>
          TSOSI data includes information on financial transfers made to support
          open science infrastructure.
        </li>
        <li>
          The content of the TSOSI website includes the text present on all the
          pages of the site.
        </li>
        <li>
          Unless otherwise stated, both the data and the content are licensed
          with a
          <a
            href="https://creativecommons.org/licenses/by-sa/4.0/"
            target="_blank"
            rel="noopener noreferrer"
          >
            CC BY-SA 4.0 license </a
          >. Collecting, using, and reusing part or all of this data and content
          must be done in accordance under the terms of the CC BY-SA license.
        </li>
      </ol>

      <h2>Copyright</h2>
      <p>
        Copyright of this website and the intellectual property contained herein
        is owned by Université Grenoble Alpes, 621 Avenue Centrale, 38400
        Saint-Martin-d'Hères, France. All defaults to all rights reserved unless
        otherwise specified. Contact TSOSI
        <EmailAtom user="contact" domain="tsosi.org" :as-mail-to="true" />.
      </p>

      <h2>Disclaimer</h2>
      <p>
        The Université Grenoble Alpes cannot, in any way, be held liable for the
        content of the information found on this website or for any consequences
        that may result from its use or interpretation.
      </p>

      <h2>Hypertext links</h2>
      <p>
        The establishment of hypertext links by third parties to pages or
        documents distributed on this site is authorized, provided that the
        links do not contravene the interests of the Université Grenoble Alpes,
        and that they allow users to identify the origin and author of the
        document.
      </p>

      <h2>Protection of personal data</h2>
      <p>
        Information on personal data protection for this site is available on
        the
        <RouterLink to="/pages/privacy-policy/">
          Privacy policy page </RouterLink
        >.
      </p>

      <h2>Publication Director</h2>
      <p>Yassine Lakhnech, President of the University of Grenoble Alpes.</p>

      <h2>Web host</h2>
      <p>
        Université Grenoble Alpes
        <br />
        Direction générale déléguée au Système d'information
        <br />
        41 rue des mathématiques, 38610 Gières, France
      </p>

      <h2>Project host</h2>
      <p>
        The project is hosted by GRICAD, Grenoble Alps Research Scientific
        Computing and Data Infrastructure,
        <a
          href="https://gricad.univ-grenoble-alpes.fr"
          target="_blank"
          rel="noopener noreferrer"
        >
          gricad.univ-grenoble-alpes.fr </a
        >.
      </p>

      <h2>Credits</h2>
      <ul>
        <li>Project leader: Maxence Larrieu</li>
        <li>Data and web engineer: Guillaume Alzieu</li>
        <li>Logo: Gilles Esparbet</li>
      </ul>
    </template>
  </StaticContentComponent>
</template>
