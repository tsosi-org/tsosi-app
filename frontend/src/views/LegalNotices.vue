<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Legal notices">
    <template #default>
      <h1>WORK IN PROGRESS</h1>

      <h2>TSOSI legal entity presentation</h2>
      <p>
        Hosted by UGA/CNRS, in the form of a ???.
        <br />
        Address.
        <br />
        Contact e-mail.
      </p>

      <h2>General terms and conditions of use</h2>

      <ol>
        <li>
          <strong>Privacy policy</strong>
          <p>
            Only browing logs are collected.
            <br />
            Please visit our
            <RouterLink to="/pages/privacy-policy">Privacy policy</RouterLink>
            page for detailed information.
          </p>
        </li>

        <li>
          <strong>Disclaimer</strong>
          <p>
            Disclaimer about the accuracy of the content.
            <br />
            Disclaimer about the data collected from ROR and Wikidata. Ex:
            <br />
            The logos used on the infrastructure and institution pages are
            collected from Wikimedia commons via Wikidata.
            <br />
            The name, country and location details are retrieved from both the
            <a
              href="https://ror.org/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Research Organization Registry</a
            >
            and
            <a
              href="https://www.wikidata.org/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Wikidata </a
            >.
          </p>
        </li>

        <li>
          <strong>Cookies</strong>
          <p>We do not use cookies on our website.</p>
        </li>
      </ol>
    </template>
  </StaticContentComponent>
</template>
