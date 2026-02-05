<script setup lang="ts">
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue";
import ImageAtom from "@/components/atoms/ImageAtom.vue";
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue";
import StaticContentComponent from "@/views/StaticContentView.vue";
</script>

<template>
  <StaticContentComponent title="About">
    <template #default>
      <p style="text-align: center; font-size: 1.5rem; padding: 1rem 0">
        <!-- bigger font like a header text, try centered text also-->
        TSOSI makes support for open infrastructure visible. It shows which
        organizations financially support which open infrastructures. By making
        this visible, TSOSI helps turn support for open infrastructure into
        common practice. Institutions, infrastructures, consortia, and others
        are really welcome to join TSOSI: let’s make support for open
        infrastructure the norm!
      </p>

      <StaticSectionAtom id="how-it-started" title="How it started">
        <p>
          TSOSI officially launched in September 2024 with funding from the
          <ExternalLinkAtom
            :href="'https://www.ouvrirlascience.fr/home/'"
            :label="'French Committee for Open Science'"
          />. It is led by
          <ExternalLinkAtom
            :href="'https://www.univ-grenoble-alpes.fr/english/'"
            :label="'Université Grenoble Alpes'"
          />
          in France. The idea originated in 2020 within a research library: if
          everyone can see which organizations have supported an open
          infrastructure,then the decision to contribute financially would
          become much more evident.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="approach" title="Approach">
        <p>
          Like
          <ExternalLinkAtom :href="'https://scoss.org'" :label="'SCOSS'" />,
          TSOSI shares the same goal: to improve the sustainability of open
          science infrastructure. To make worldwide research a common good,
          research needs infrastructure that allows research stakeholders to
          practice open science. The original approach of TSOSI relies on its
          data-driven approach. TSOSI disseminates data that represents choices
          that are coherent with the values of open science. When an
          organisation financially supports an infrastructure, it produces data,
          at least: the funder, the beneficiary, the date, and the amount of the
          support. TSOSI collects, enriches, and organises these data to give
          visibility to all those who have financially contributed to open
          science infrastructure. TSOSI data represent choices made to support
          open infrastructure: the more we disseminate these data, the more
          evident the choices made to support open infrastructure will be.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="governance" title="Governance">
        <p>
          The governance structure consists of an advisory board, a user group,
          and a supervision group. PeerCommunityIn, SciPost, and Couperin are
          part of the user group. DOAJ, DOAB, OPERAS, and SCOSS are members of
          the advisory board. Finally, the French Committee for Open Science and
          Grenoble Alpes University are members of the supervision group.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom
        id="open-data-and-software"
        title="Open data and software"
      >
        <p>
          TSOSI is dedicated to openness; we produce open software and open
          data. The platform's software is shared on
          <ExternalLinkAtom
            :href="'https://github.com/tsosi-org'"
            :label="'GitHub'"
          />, and the data is accessible via an API, see how to use it in the
          <ExternalLinkAtom
            :href="'https://github.com/tsosi-org/api-use-cases'"
            :label="'api-use-cases'"
          />
          repository.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="related-initiatives" title="Related initiatives">
        <p>
          Concerning TSOSI's goal, we are delighted to work with
          <ExternalLinkAtom :href="'https://scoss.org'" :label="'SCOSS'" />,
          which has organized an annual funding call since 2018 to support three
          to four infrastructures. TSOSI is also closely aligned with Invest in
          Open, particularly through the
          <ExternalLinkAtom
            :href="'https://infrafinder.investinopen.org/solutions'"
            :label="'Infra Finder'"
          />
          tool. If an infrastructure is within the scope of SCOSS or Infra
          Finder, this is indicated on its page on the TSOSI platform. TSOSI is
          also closely connected to the
          <ExternalLinkAtom
            :href="'https://barcelona-declaration.org/'"
            :label="'Declaration of Barcelona on Open Research Information'"
          />, whose signatories are committed to supporting the sustainability
          of infrastructure. TSOSI is also related to the
          <ExternalLinkAtom
            :href="'https://openscholarlyinfrastructure.org/'"
            :label="'Principles of Open Scholarly Infrastructure'"
          />, a set of guidelines for the governance and sustainability of open
          scholarly infrastructure. For its data-driven approach, TSOSI has been
          highly inspired by
          <ExternalLinkAtom
            :href="'https://openapc.net/'"
            :label="'OpenAPC'"
          />. Moreover, the initiative
          <ExternalLinkAtom
            :href="'https://www.opencost.de/en/'"
            :label="'openCost'"
          />
          started in 2021, which permits research institutions to practise open
          data about financial contributions for open infrastructure, is highly
          connected to TSOSI. The technical design of the platform has been
          inspired by the famous work of
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
      </StaticSectionAtom>

      <StaticSectionAtom id="contact" title="Contact">
        <p>
          We welcome your inquiries and feedback. Please
          <RouterLink :to="'/pages/faq#contact-us'">contact us</RouterLink>. We
          look forward to hearing from you.
        </p>
      </StaticSectionAtom>

      <StaticSectionAtom id="credits" title="Credits">
        <ul>
          <li>
            Maxence Larrieu
            <ExternalLinkAtom :href="'https://orcid.org/0000-0002-1834-3007'">
              <ImageAtom
                :src="'/img/orcid_badge.svg'"
                :width="'1em'"
                :container-padding="'0'"
                style="display: inline-block; margin-right: 4px"
              />
            </ExternalLinkAtom>
            - Project leader
          </li>
          <li>
            Baptiste Lefeuvre - Data and web engineer
          </li>
          <li>
            Guillaume Alzieu - Project engineer [2024-2025]
          </li>
        </ul>
        <p>
          Both are based at Grenoble Alpes University, within the
          <ExternalLinkAtom
            :href="'https://gricad.univ-grenoble-alpes.fr/en/'"
            :label="'GRICAD research unit'"
          />, which operates the TSOSI platform.
        </p>
      </StaticSectionAtom>
    </template>
  </StaticContentComponent>
</template>
