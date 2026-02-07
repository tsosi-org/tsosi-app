<script setup lang="ts">
import { $dt } from "@primevue/themes"
import { RouterLink } from "vue-router"

import ExternalLinkAtom from "@/components/atoms/ExternalLinkAtom.vue"
import NavigationListAtom from "@/components/atoms/NavigationListAtom.vue"
import { isDesktop } from "@/composables/useMediaQuery"
</script>

<template>
  <footer>
    <div class="container footer-wrapper" :class="{ desktop: isDesktop }">
      <div class="footer-data">
        <div class="logo">
          <img src="@/assets/img/logo_white.svg" />
        </div>
        <div class="copyright">
          &copy; 2025 TSOSI under a
          <RouterLink to="/pages/legal-notice">
            Creative Commons BY-SA license</RouterLink
          >.
        </div>
        <div class="legal">
          <RouterLink to="/pages/legal-notice">Legal notice</RouterLink> &bull;
          <RouterLink to="/pages/privacy-policy">Privacy policy</RouterLink>
        </div>
        <div class="backers">
          Led by
          <ExternalLinkAtom
            :label="'Université Grenoble Alpes'"
            :href="'https://www.univ-grenoble-alpes.fr/english/'"
          />
          <br />
          Funded by
          <ExternalLinkAtom
            :label="'The French National Fund for Open Science'"
            :href="'https://www.ouvrirlascience.fr/national-fund-for-open-science/'"
          />
          <br />
          Operated by
          <ExternalLinkAtom
            :label="'Grenoble Alpes Research Scientific Computing and Data Infrastructure'"
            :href="'https://gricad.univ-grenoble-alpes.fr/en/'"
          />
        </div>
      </div>
      <div class="footer-links">
        <h3>Community</h3>
        <ul>
          <li>
            <ExternalLinkAtom href="https://github.com/tsosi-org">
              <font-awesome-icon
                :icon="['fab', 'github']"
                class="link-icon"
              />Github
            </ExternalLinkAtom>
          </li>
          <li>
            <RouterLink to="/pages/newsletter">
              <font-awesome-icon
                :icon="['fas', 'envelope']"
                class="link-icon"
              />Newsletter
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/pages/faq#contact-us">
              <font-awesome-icon
                :icon="['fas', 'at']"
                class="link-icon"
              />Contact
            </RouterLink>
          </li>
        </ul>
      </div>
      <div class="footer-nav">
        <h3>Navigation</h3>
        <NavigationListAtom
          :color="$dt('neutral.50').value"
        />
      </div>
    </div>
  </footer>
</template>

<style scoped>
footer {
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

  & .backers {
    margin-top: 2.45rem; /* Margin used to align the end of the content with the infrastructures column end */
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

.backers {
  line-height: 1.5;
  & :deep(a) {
    text-decoration: underline;
  }
}

.link-icon {
  margin-right: 0.5em;
}
</style>
