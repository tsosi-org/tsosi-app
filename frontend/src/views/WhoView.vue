<script setup lang="ts">
import Member from "@/components/atoms/MemberAtom.vue"
import StaticSectionAtom from "@/components/atoms/StaticSectionAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Who we are ?">
    <StaticSectionAtom id="steering-comittee" title="Steering Committee">
      <div class="container">
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
    <StaticSectionAtom id="advisory-group" title="Advisory Group">
      <div class="container">
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
    <StaticSectionAtom id="user-group" title="User Group">
      <div class="container">
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
    <StaticSectionAtom id="operational-team" title="Operational team">
      <div class="container">
        <Member name="Baptiste Lefeuvre" role="GRICAD, CNRS, UGA"> </Member>
        <Member
          name="Maxence Larrieu"
          role="Université Grenoble Alpes"
          orcid="https://orcid.org/0000-0002-1834-3007"
        >
        </Member>
      </div>
    </StaticSectionAtom>
  </StaticContentComponent>
</template>

<style scoped>
.container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 30px;
  margin-bottom: 30px;
}
</style>
