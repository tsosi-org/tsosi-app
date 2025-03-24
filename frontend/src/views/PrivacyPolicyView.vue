<script setup lang="ts">
import StaticContentComponent from "@/views/StaticContentView.vue"
</script>

<template>
  <StaticContentComponent title="Privacy policy">
    <template #default>
      <p><strong>Last updated:</strong> <i>2025-03-21</i></p>
      <p>
        This Privacy Policy explains how we collect, use, and safeguard your
        data when you visit our website, in accordance with European data
        protection laws, including the General Data Protection Regulation
        (GDPR).
      </p>

      <h2>Collected data</h2>
      <p>We collect browsing logs when you visit our website:</p>
      <ul>
        <li>Your IP address</li>
        <li>Date</li>
        <li>Request made (in the form of a URL)</li>
        <li>Browser type</li>
        <li>Response status (HTTP status code)</li>
      </ul>

      <h2>Purpose of data collection</h2>
      <p>The data we collect is used for the following purposes:</p>
      <ul>
        <li>
          <strong>Website analytics</strong>
          <br />
          To analyze and monitor website traffic, including the number of
          visitors, the pages accessed, and other technical metrics.
        </li>
        <li>
          <strong>Troubleshooting and security</strong>
          <br />
          To identify and resolve any technical issues with the website, as well
          as to detect and prevent any security incidents.
        </li>
      </ul>

      <h2>Recipient of the data collection</h2>
      <p>
        The data we collect is only used by the people working for the TSOSI
        project to perform the previously listed tasks.
      </p>

      <h2>Legal basis for data processing</h2>
      <p>
        We process the data we collect based on
        <strong>legitimate interests</strong>. The processing of your data is
        necessary for the legitimate interests pursued by us, including
        improving the functionality of our website, ensuring its security, and
        maintaining traffic analysis.
      </p>

      <h2>Data retention</h2>
      <p>
        We retain the logged data only for as long as necessary for the purposes
        stated above. This data is kept for a period not exceeding 6 months,
        after which it is securely deleted.
      </p>

      <h2>Your rights</h2>
      <p>
        You are allowed to request access, rectification, erasure, restriction
        or portability of your personal data collected on our website. To
        exercise any of these rights, please contact us using our contact
        details
      </p>

      <h2>Changes to this privacy policy</h2>
      <p>
        We may update this Privacy Policy. Any changes will be posted on this
        page, and we will update the "Last Updated" date at the top of this
        policy. We encourage you to review this policy periodically to stay
        informed about how we are protecting your information.
      </p>
    </template>
  </StaticContentComponent>
</template>
