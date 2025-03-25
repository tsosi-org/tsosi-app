<script setup lang="ts">
import { RouterLink } from "vue-router"
import NavigationListAtom from "@/components/atoms/NavigationListAtom.vue"
import { $dt } from "@primevue/themes"
import { isDesktop } from "@/composables/useMediaQuery"
import InfrastructureList from "@/components/atoms/InfrastructureList.vue"
</script>

<template>
  <footer>
    <div class="container footer-wrapper" :class="{ desktop: isDesktop }">
      <div class="footer-data">
        <div class="logo">
          <img src="@/assets/img/logo_white.svg" />
        </div>
        <div class="copyright">
          &copy; TSOSI 2025 default by all rights reserved
          <RouterLink to="/pages/legal-notice">
            unless otherwise specified </RouterLink
          >.
        </div>
        <div class="legal">
          <RouterLink to="/pages/legal-notice">Legal notice</RouterLink> &bull;
          <RouterLink to="/pages/privacy-policy">Privacy policy</RouterLink>
        </div>
      </div>
      <div class="footer-nav">
        <h3>Navigation</h3>
        <NavigationListAtom
          :color="$dt('neutral.50').value"
          font-size="1em"
          style="--gap: 0"
        />
      </div>
      <div class="footer-partners">
        <h3>Infrastructures</h3>
        <InfrastructureList />
      </div>
    </div>
  </footer>
</template>

<style scoped>
footer {
  margin-top: 2em;
  line-height: 2.5;
  color: var(--p-neutral-50);
  background-color: var(--p-neutral-950);
  padding: 5vh 0;

  /* Override variables define in some child componentss */
  & :deep(a) {
    color: inherit;
    font-size: inherit;
    line-height: inherit;
    padding: inherit;
    text-decoration: unset;
  }
  & :deep(a):hover,
  & :deep(a):focus-visible {
    text-decoration: underline;
  }
}

.footer-wrapper {
  --after-height: 2px;
  padding: 2em;

  h3 {
    color: inherit;
    font-size: 1.8em;
    margin: 0;
  }

  & > * {
    position: relative;
    padding-top: calc(2em + var(--after-height));
    padding-bottom: 2em;
  }

  & > *::after {
    content: "";
    height: var(--after-height);
    width: 100%;
    background-color: var(--p-neutral-400);
    position: absolute;
    bottom: 0;
  }

  & > *:last-child::after {
    all: unset;
  }
}

.footer-wrapper.desktop {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  column-gap: 2em;

  & > * {
    padding: 0;
  }

  & > *::after {
    all: unset;
  }

  h3 {
    margin: 1.25rem 0;
  }
}

.footer-wrapper > * > * {
  margin-bottom: 1em;
}

.footer-wrapper > * > *:last-child {
  margin-bottom: inherit;
}

ul {
  list-style: none;
  padding: unset;
}

.logo img {
  max-width: 14em;
}

.logo-inline {
  display: inline;
  height: 2em;
  padding: 0.1em;
  filter: invert(0.5);
  margin-bottom: -0.7em;
}

.copyright {
  color: var(--p-neutral-400);

  & a {
    text-decoration: underline;
  }
}
</style>
