<script setup lang="ts">
import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import Member from "@/components/atoms/MemberAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import { useContactModal } from "@/composables/useContactModal"
import StaticContentComponent from "@/views/StaticContentView.vue"
import Divider from "primevue/divider"
const { openContactModal } = useContactModal()
</script>

<template>
  <StaticContentComponent title="About">
    <template #default>
      <div class="navigation-list">
        <RouterLink to="#how-it-started">How it started</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#approach">Approach</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#who-we-are">Who we are</RouterLink>
        <Divider layout="vertical" />
        <RouterLink to="#open-data-and-software"
          >Open data and software</RouterLink
        >
        <Divider layout="vertical" />
        <RouterLink to="#related-initiatives">Related initiatives</RouterLink>
      </div>
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

      <StaticSectionAtom id="who-we-are" title="Who we are">
        <StaticSectionAtom
          id="steering-comittee"
          title="Steering Committee"
          :noLink="true"
        >
          <div class="member-container">
            <Member
              name="Marin Dacos"
              role="Ministry of Higher Education, Research and Space"
              orcid="https://orcid.org/0000-0002-9361-5295"
            >
            </Member>
            <Member
              name="Suzanne Dumouchel"
              role="CNRS"
              orcid="https://orcid.org/0000-0002-3569-532X"
            >
            </Member>
            <Member
              name="Maxence Larrieu"
              role="Université Grenoble Alpes"
              orcid="https://orcid.org/0000-0002-1834-3007"
            >
            </Member>
          </div>
        </StaticSectionAtom>
        <StaticSectionAtom
          id="advisory-group"
          title="Advisory Group"
          :noLink="true"
        >
          <div class="member-container">
            <Member
              name="Niels Stern"
              role="DOAB"
              orcid="https://orcid.org/0000-0001-6466-9748"
            >
            </Member>
            <Member
              name="Joanna Ball"
              role="DOAJ"
              orcid="https://orcid.org/0000-0002-4033-9119"
            >
            </Member>
            <Member
              name="Vanessa Proudman"
              role="SparcEurope"
              orcid="https://orcid.org/0000-0001-5623-9051"
            >
            </Member>
          </div>
        </StaticSectionAtom>
        <StaticSectionAtom id="user-group" title="User Group" :noLink="true">
          <div class="member-container">
            <Member
              name="Denis Bourguet"
              role="PeerCommunityIn"
              orcid="https://orcid.org/0000-0002-2109-5323"
            >
            </Member>
            <Member name="Thomas Guillemaud" role="PeerCommunityIn"> </Member>
            <Member
              name="Jean-Sebastien Caux"
              role="SciPost"
              orcid="https://orcid.org/0000-0001-9322-5011"
            >
            </Member>
            <Member
              name="Marlène Delhaye"
              role="Couperin"
              orcid="https://orcid.org/0000-0001-6306-5774"
            >
            </Member>
          </div>
        </StaticSectionAtom>
        <StaticSectionAtom
          id="operational-team"
          title="Operational team"
          :noLink="true"
        >
          <div class="member-container">
            <Member name="Baptiste Lefeuvre" role="GRICAD, CNRS, UGA"> </Member>
            <Member
              name="Maxence Larrieu"
              role="Université Grenoble Alpes"
              orcid="https://orcid.org/0000-0002-1834-3007"
            >
            </Member>
          </div>
        </StaticSectionAtom>
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
    </template>
  </StaticContentComponent>
</template>

<style scoped>
.member-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 30px;
  margin-bottom: 30px;
}

.navigation-list {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  margin-bottom: 50px;
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
</style>
