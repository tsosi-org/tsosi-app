<script setup lang="ts">
import CodeBlockAtom from "@/components/atoms/CodeBlockAtom.vue"
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Privacy policy">
    <template #default>
      <p>
        The TSOSI project's mission is to foster the sustainability of open
        science infrastructures. In this context, Université Grenoble Alpes is
        required to collect and use personal information such as IP addresses,
        browsers, and the terminals used.
        <br />
        The implementation of this site has therefore undergone a compliance
        review by the Data Protection Officer. The personal information
        collected is processed in accordance with the General Data Protection
        Regulation (EU) 2016/679 of the European Parliament and of the Council
        of April 27, 2016 (GDPR), as well as the 'Informatique et libertés' law
        of January 6, 1978, as amended.
      </p>

      <h2>Purpose of data collection</h2>
      <p>The data we collect is used for the following purposes:</p>
      <ul>
        <li>
          <strong>Website analytics</strong>
          <br />
          To analyze and monitor website traffic, including the number of
          visitors, their location and the pages accessed.
        </li>
        <li>
          <strong>Troubleshooting and security</strong>
          <br />
          To identify and resolve any technical issues with the website, as well
          as to detect and prevent any security incidents.
        </li>
      </ul>

      <h2>Collected data</h2>
      <p>We collect browsing logs when you visit our website:</p>
      <ul>
        <li>Your IP address</li>
        <li>Date</li>
        <li>Request made (in the form of a URL)</li>
        <li>Browser type</li>
        <li>Response status (HTTP status code)</li>
      </ul>

      <h2>Recipient of the data collection</h2>
      <p>
        The data we collect is only used by the members of the TSOSI project to
        perform the previously listed tasks.
        <br />
        The data is stored on the information technology servers of the
        Université Grenoble Alpes.
      </p>

      <h2>Data retention</h2>
      <p>
        We retain the logged data only for as long as necessary for the purposes
        stated above. This data is kept for a period not exceeding 24 months,
        after which it is securely deleted.
      </p>

      <h2>Your rights</h2>
      <p>
        You have the right to access, rectify, erase, limit, and the right to
        data portability concerning your information, which you can exercise by
        contacting:
        <br />
        <br />
        Université Grenoble Alpes
        <br />
        GRICAD
        <br />
        150 place du Torrent 38400
        <br />
        Saint Martin d'Hères, France
        <br />
        <br />
        <CodeBlockAtom
          :content="'contact (tsosi.org)'"
          :inline="true"
          :background="true"
        />
      </p>

      <h2>Changes to this privacy policy</h2>
      <p>
        We may update this Privacy Policy. Any changes will be posted on this
        page, and we will update the "Last Updated" date of this policy.
      </p>

      <br />

      <p><strong>Last updated:</strong> <i>2025-03-25</i></p>
    </template>
  </StaticContentComponent>
</template>
