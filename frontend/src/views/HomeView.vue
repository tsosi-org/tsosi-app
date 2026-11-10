<script setup lang="ts">
import { computed, onBeforeMount, onMounted, onUnmounted, ref } from "vue"

import cosoLogoUrl from "@/assets/img/coso_logo_couleur.svg"
import couperinLogoUrl from "@/assets/img/couperin_logo.png"
import doajLogoUrl from "@/assets/img/doaj_logo.svg"
import gricadLogoUrl from "@/assets/img/logo_gricad_couleur.png"
import ugaLogoUrl from "@/assets/img/logo_UGA_couleur.svg"
import mesrLogoUrl from "@/assets/img/mesr_logo_couleur.png"
import oapenDoabLogoUrl from "@/assets/img/oapen_doab_logo.png"
import pciLogoUrl from "@/assets/img/pci_logo.png"
import scipostLogoUrl from "@/assets/img/scipost_logo.png"
import scossLogoUrl from "@/assets/img/scoss_logo.png"
import ExternalLink from "@/components/atoms/ExternalLinkAtom.vue"
import { get } from "@/services/api"
import { setBigHeader, togglePageNoHeader } from "@/singletons/fixedHeaderStore"
import {
  getEmitters,
  getInfrastructures,
  getPartners,
  type Entity,
} from "@/singletons/ref-data"
import { shuffleArray } from "@/utils/data-utils"
import { getEntityUrl } from "@/utils/url-utils"

onBeforeMount(() => {
  setBigHeader(true)
  togglePageNoHeader(true)
})

onMounted(() => {
  window.addEventListener("scroll", updateHeaderHome)
  loadFigures()
  loadNews()
})

onUnmounted(() => {
  setBigHeader(false)
  togglePageNoHeader(false)
  window.removeEventListener("scroll", updateHeaderHome)
})

function updateHeaderHome() {
  setBigHeader(window.scrollY < 70)
}

const MOSAIC_SIZE = 15
const partners = getPartners() as Entity[]
const partnersWithLogo = partners.filter((e) => e.logo)
shuffleArray(partnersWithLogo)
const mosaicPartners = partnersWithLogo.slice(0, MOSAIC_SIZE)

function tilePosition(k: number) {
  return { "--i": Math.floor(k / 4), "--j": k % 4 }
}

const emitters = getEmitters()
const countryCount = new Set(emitters.map((e) => e.country).filter((c) => c))
  .size
const infrastructureCount = getInfrastructures().length

interface HomeFigures {
  supports: number
  amount_usd: number
  date_data_update: string | null
}

const homeFigures = ref<HomeFigures | null>(null)

async function loadFigures() {
  const result = await get("home-figures", true)
  if (!result.error && result.data) {
    homeFigures.value = result.data as HomeFigures
  }
  animateCount()
}

const numberFormat = new Intl.NumberFormat("en-US")
const amountFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
})

// Figures count up from 0 once the API figures are loaded
const COUNT_DURATION = 1400
const countProgress = ref(0)

function animateCount() {
  const start = performance.now()
  const step = (now: number) => {
    const t = Math.min((now - start) / COUNT_DURATION, 1)
    countProgress.value = 1 - (1 - t) ** 3 // ease-out
    if (t < 1) {
      requestAnimationFrame(step)
    }
  }
  requestAnimationFrame(step)
}

function countUp(value: number, format: Intl.NumberFormat): string {
  return format.format(Math.round(value * countProgress.value))
}

const figures = computed(() => [
  {
    value: countUp(emitters.length, numberFormat),
    label: "supporting organizations",
  },
  {
    value: countUp(infrastructureCount, numberFormat),
    label: "infrastructures",
  },
  { value: countUp(countryCount, numberFormat), label: "countries" },
  {
    value: homeFigures.value
      ? countUp(homeFigures.value.supports, numberFormat)
      : "–",
    label: "financial contributions",
  },
  {
    value: homeFigures.value
      ? countUp(homeFigures.value.amount_usd, amountFormat)
      : "–",
    label: "total of all contributions",
  },
])

function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

// News, picked on the GitHub "Homepage news" board (backend `tsosi/data/news.py`)
type NewsKind = "linkedin" | "blog" | "newsletter" | "other"

interface NewsItem {
  kind: NewsKind
  title: string
  text: string
  url: string
  date: string | null
  image: string | null
  image_alt: string
}

const newsLabels: Record<NewsKind, string> = {
  linkedin: "LinkedIn",
  blog: "Blog",
  newsletter: "Newsletter",
  other: "News",
}

const newsLinkTexts: Record<NewsKind, string> = {
  linkedin: "Read on LinkedIn",
  blog: "Read the post",
  newsletter: "Read the newsletter",
  other: "Read more",
}

const news = ref<NewsItem[]>([])

async function loadNews() {
  const result = await get("news", true)
  if (!result.error && Array.isArray(result.data) && result.data.length) {
    news.value = result.data as NewsItem[]
    return
  }
  // Until news are picked on the board
  const post = await fetchLatestBlogPost()
  if (post) {
    news.value = [post]
  }
}

async function fetchLatestBlogPost(): Promise<NewsItem | null> {
  const res = await fetch("/pages/blog/index.json").catch(() => null)
  if (!res?.ok) {
    return null
  }
  const data = await res.json().catch(() => null)
  const post = data?.posts?.[0]
  if (!post) {
    return null
  }
  return {
    kind: "blog",
    title: post.title,
    text: htmlToText(post.summary),
    url: `/pages/blog/${post.permalink.split("/")[2]}/`,
    date: post.date,
    image: null,
    image_alt: "",
  }
}

/**
 * The route of the blog posts and newsletters, opened in the app.
 */
function newsRoute(item: NewsItem): string | null {
  if (item.kind != "blog" && item.kind != "newsletter") {
    return null
  }
  return new URL(item.url, window.location.origin).pathname
}

function htmlToText(html: string): string {
  return (
    new DOMParser().parseFromString(html, "text/html").body.textContent || ""
  )
    .replace(/\s+/g, " ")
    .trim()
}

const linkedInUrl = "https://www.linkedin.com/company/tsosi/"

// Governance
const leadLogos = [
  {
    name: "Université Grenoble Alpes",
    src: ugaLogoUrl,
    href: "https://www.univ-grenoble-alpes.fr/en",
    size: 72,
  },
  {
    name: "GRICAD",
    src: gricadLogoUrl,
    href: "https://gricad.univ-grenoble-alpes.fr/en/",
    size: 84,
  },
  {
    name: "French Ministry of Higher Education, Research and Space",
    src: mesrLogoUrl,
    href: "https://www.enseignementsup-recherche.gouv.fr/fr",
    size: 100,
  },
  {
    name: "French Committee for Open Science (Ouvrir la science)",
    src: cosoLogoUrl,
    href: "https://www.ouvrirlascience.fr/home/",
    size: 46,
  },
]

const memberLogos = [
  {
    name: "OAPEN & DOAB",
    src: oapenDoabLogoUrl,
    href: "https://www.doabooks.org/",
    size: 58,
  },
  {
    name: "Directory of Open Access Journals",
    src: doajLogoUrl,
    href: "https://doaj.org/",
    size: 44,
  },
  {
    name: "SCOSS",
    src: scossLogoUrl,
    href: "https://scoss.org/",
    size: 53,
  },
  {
    name: "Peer Community In",
    src: pciLogoUrl,
    href: "https://peercommunityin.org/",
    size: 84,
  },
  {
    name: "SciPost",
    src: scipostLogoUrl,
    href: "https://scipost.org/",
    size: 53,
  },
  {
    name: "Couperin",
    src: couperinLogoUrl,
    href: "https://www.couperin.org/",
    size: 75,
  },
]
</script>

<template>
  <div id="home">
    <!-- Hero -->
    <section class="hero" aria-labelledby="hero-title">
      <div class="container hero-main">
        <div class="hero-text">
          <h1 id="hero-title">
            Making support for open infrastructures visible
          </h1>
          <p class="lead">
            TSOSI gathers financial support provided to open infrastructures,
            organizes this data with identifiers and then makes it openly
            available to everyone
          </p>
          <div class="hero-actions">
            <RouterLink to="/explore" class="btn btn-primary">
              Explore the data
              <font-awesome-icon :icon="['fas', 'arrow-right']" />
            </RouterLink>
            <!-- <RouterLink to="/new-provider" class="strong-link">
              Become a data provider
            </RouterLink> -->
          </div>
        </div>
        <div class="hero-mosaic">
          <ul class="mosaic" aria-label="TSOSI data providers">
            <li
              v-for="(entity, k) of mosaicPartners"
              :key="entity.id"
              :style="tilePosition(k)"
            >
              <RouterLink
                :to="getEntityUrl(entity)"
                class="dia"
                :title="entity.name"
              >
                <span class="dia-bg" aria-hidden="true"></span>
                <img :src="entity.logo" :alt="entity.name" loading="lazy" />
              </RouterLink>
            </li>
            <li :style="tilePosition(mosaicPartners.length)">
              <RouterLink
                to="/new-provider"
                class="dia dia-cta"
                title="Become a data provider"
              >
                <span class="dia-bg" aria-hidden="true"></span>
                <span class="dia-text">Your<br />logo<br />here?</span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </div>

      <div class="figures-band">
        <dl class="container figures">
          <div v-for="figure of figures" :key="figure.label" class="figure">
            <dt>{{ figure.label }}</dt>
            <dd>{{ figure.value }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- News -->
    <section class="band band-light" aria-labelledby="news-title">
      <div class="container stack">
        <div class="section-head">
          <h2 id="news-title">Latest news</h2>
          <div class="section-links">
            <ExternalLink :href="linkedInUrl">LinkedIn</ExternalLink>
            <RouterLink to="/pages/blog">Blog</RouterLink>
            <RouterLink to="/pages/newsletter">Newsletter</RouterLink>
          </div>
        </div>
        <div class="news-row">
          <article
            v-for="(item, index) of news"
            :key="`${index}-${item.url}`"
            class="news-card"
          >
            <div v-if="item.image" class="news-media">
              <img
                :src="item.image"
                :alt="item.image_alt"
                class="news-image"
                loading="lazy"
              />
            </div>
            <div v-else class="news-media news-media-dark">
              <img src="@/assets/img/logo_white.svg" alt="" />
            </div>
            <div class="news-body">
              <p class="news-meta">
                {{ newsLabels[item.kind] }}
                <template v-if="item.date">
                  · {{ formatDate(item.date) }}
                </template>
              </p>
              <h3 v-if="item.title">{{ item.title }}</h3>
              <p
                v-if="item.text"
                :class="item.kind == 'linkedin' ? 'news-text' : 'news-summary'"
                v-text="item.text"
              ></p>
              <RouterLink
                v-if="newsRoute(item)"
                :to="newsRoute(item)!"
                class="strong-link"
              >
                {{ newsLinkTexts[item.kind] }}
              </RouterLink>
              <ExternalLink v-else :href="item.url" class="strong-link">
                {{ newsLinkTexts[item.kind] }}
              </ExternalLink>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- What TSOSI does -->
    <section class="band" aria-labelledby="what-title">
      <div class="container stack">
        <h2 id="what-title">What TSOSI does</h2>
        <div class="missions">
          <div class="mission">
            <font-awesome-icon :icon="['fas', 'eye']" class="mission-icon" />
            <h3>We make financial support for open infrastructures visible</h3>
            <p>
              Each support links an institution to an infrastructure, with a
              year and an amount.
            </p>
          </div>
          <div class="mission">
            <font-awesome-icon
              :icon="['fas', 'scale-balanced']"
              class="mission-icon"
            />
            <h3>We bring transparency to funding policies</h3>
            <p>
              Institutions can show what they contribute and see how others do.
            </p>
          </div>
          <div class="mission">
            <font-awesome-icon
              :icon="['fas', 'magnifying-glass']"
              class="mission-icon"
            />
            <h3>We help users explore who funds open infrastructures</h3>
            <p>
              Search by institutions, infrastructure or country, and reuse the
              data through the open API.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Governance -->
    <section class="band band-light" aria-labelledby="gov-title">
      <div class="container stack">
        <h2 id="gov-title">Governed by the research community</h2>
        <div class="governance-lead">
          <div class="governance-text">
            <p>
              TSOSI is led by <b>Université Grenoble Alpes</b>, funded by the
              <b>French National Fund for Open Science</b>, and operated by
              <b>GRICAD</b>.
              <RouterLink to="/pages/about#who-we-are" class="strong-link">
                See more about our governance
              </RouterLink>
            </p>
          </div>
          <div class="logo-row lead-logos">
            <ExternalLink
              v-for="logo of leadLogos"
              :key="logo.name"
              :href="logo.href"
              class="logo-link"
            >
              <img
                :src="logo.src"
                :alt="logo.name"
                :style="{ height: `${logo.size}px` }"
              />
            </ExternalLink>
          </div>
        </div>
        <div class="governance-members">
          <div class="logo-row member-logos">
            <ExternalLink
              v-for="logo of memberLogos"
              :key="logo.name"
              :href="logo.href"
              class="logo-link"
            >
              <img
                :src="logo.src"
                :alt="logo.name"
                :style="{ height: `${logo.size}px` }"
              />
            </ExternalLink>
          </div>
        </div>
      </div>
    </section>

    <!-- Call to action -->
    <section class="band" aria-labelledby="cta-title">
      <div class="container">
        <div class="cta">
          <div class="cta-text">
            <h2 id="cta-title">
              Does your organization support open infrastructures?
            </h2>
            <p>
              Follow the {{ partners.length }} organizations that have already
              shared data with TSOSI, and make your support visible!
            </p>
          </div>
          <RouterLink to="/new-provider" class="btn btn-dark">
            Become a data provider
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
#home {
  --home-text: var(--p-primary-900);
  --home-muted: var(--p-primary-700);
  --home-border: #dfe6ee;
  --home-light: #f3f6f9;
  --home-accent: #e7a925;
  --home-link: #1d6c95;
  --section-space: clamp(96px, 11vw, 152px);
  --block-space: clamp(28px, 3vw, 40px);

  color: var(--home-text);
  font-size: 16px;
  line-height: 1.6;

  & h1,
  & h2,
  & h3 {
    color: var(--home-text);
    margin: 0;
  }

  & h2 {
    font-size: clamp(28px, 3vw, 38px);
    line-height: 1.2;
  }

  & h3 {
    font-size: 21px;
    line-height: 1.3;
  }

  & p {
    margin: 0;
  }

  & ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
}

/* Shared pieces */
.band {
  padding-block: calc(var(--section-space) / 2);

  &.band-light {
    background-color: var(--home-light);
  }
}

.stack {
  display: flex;
  flex-direction: column;
  gap: var(--block-space);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px 32px;
  flex-wrap: wrap;
}

.section-links {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 15px;
}

.section-links a,
.strong-link {
  color: var(--home-link);
  font-weight: 700;

  &:hover {
    color: var(--p-primary-900);
  }
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 52px;
  padding: 14px 26px;
  border-radius: 10px;
  font-size: 17px;
  font-weight: 700;
  text-decoration: none;
  color: white;
}

.btn-primary {
  background-color: var(--home-link);

  &:hover {
    background-color: #14506f;
  }
}

.btn-dark {
  background-color: var(--p-primary-900);

  &:hover {
    background-color: var(--p-primary-700);
  }
}

.btn:focus-visible,
.logo-link:focus-visible {
  outline: 3px solid var(--home-link);
  outline-offset: 3px;
}

/* Hero */
.hero {
  background-color: var(--home-light);
  overflow: hidden;
}

.hero-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--block-space) 48px;
  padding-block: 32px;
}

.hero-text {
  flex: 1 1 420px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;

  & h1 {
    font-size: clamp(36px, 4.4vw, 56px);
    line-height: 1.08;
    text-transform: none;
    padding: 0;
    text-align: left;
  }
}

.lead {
  font-size: clamp(17px, 1.5vw, 20px);
  color: var(--home-muted);
  text-wrap: pretty;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px;
  padding-top: 8px;

  & .strong-link {
    font-size: 17px;
  }
}

.hero-mosaic {
  flex: 1 1 420px;
  min-width: 0;
  display: flex;
  justify-content: center;
}

.mosaic {
  --t: clamp(56px, 7.2vw, 120px);
  --gap: 10px;
  --d: calc(var(--t) * 1.4142);
  --h: calc((var(--t) + var(--gap)) * 0.7071);
  position: relative;
  flex: none;
  width: calc(6 * var(--h) + var(--d));
  height: calc(6 * var(--h) + var(--d));

  & li {
    position: absolute;
    width: var(--d);
    height: var(--d);
    left: calc((3 + var(--j) - var(--i)) * var(--h));
    top: calc((var(--i) + var(--j)) * var(--h));
  }
}

@media (max-width: 700px) {
  .mosaic {
    --t: 15vw;
    --gap: 2vw;
  }
}

.dia {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  /* Clicks only on the diamond, with room for the hover zoom */
  clip-path: polygon(50% -6%, 106% 50%, 50% 106%, -6% 50%);

  &:hover,
  &:focus-visible {
    z-index: 1;
    outline: none;
  }

  & img {
    position: relative;
    width: 46%;
    height: 46%;
    object-fit: contain;
  }
}

.dia-bg {
  position: absolute;
  left: 50%;
  top: 50%;
  width: var(--t);
  height: var(--t);
  transform: translate(-50%, -50%) rotate(45deg);
  background-color: white;
  border: 1.5px solid var(--p-primary-100);
  border-radius: 10px;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease;
}

.dia:hover .dia-bg,
.dia:focus-visible .dia-bg {
  transform: translate(-50%, -50%) rotate(45deg) scale(1.08);
  border-color: var(--home-link);
}

.dia:focus-visible .dia-bg {
  border-width: 3px;
}

.dia-cta {
  .dia-bg {
    background-color: var(--home-accent);
    border-color: var(--home-accent);
  }

  &:hover .dia-bg {
    background-color: #f0bd4a;
  }
}

.dia-text {
  position: relative;
  color: var(--home-text);
  font-weight: 700;
  font-size: clamp(10px, 1vw, 14px);
  line-height: 1.15;
  text-align: center;
}

/* Key figures */
.figures-band {
  border-top: 1px solid var(--home-border);
  background-color: white;
  padding-block: 28px;
}

.figures {
  margin-block: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(170px, 40%), 1fr));
  gap: 20px;
  text-align: center;
}

.figure {
  display: flex;
  flex-direction: column-reverse;
  gap: 2px;

  & dt {
    font-size: 15px;
    color: var(--home-muted);
  }

  & dd {
    margin: 0;
    font-family: Mount, Verdana, sans-serif;
    font-size: 34px;
    font-weight: 700;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }
}

/* News */
.news-row {
  --news-gap: 24px;
  display: grid;
  /* At most 3 columns, a row of fewer cards keeps their width */
  grid-template-columns: repeat(
    auto-fill,
    minmax(min(100%, max(300px, (100% - 2 * var(--news-gap)) / 3)), 1fr)
  );
  gap: var(--news-gap);
}

@media (max-width: 640px) {
  .news-row {
    grid-auto-flow: column;
    grid-template-columns: none;
    grid-auto-columns: 82%;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-bottom: 8px;

    & > * {
      scroll-snap-align: start;
    }
  }
}

.news-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: white;
  border: 1px solid var(--home-border);
  border-radius: 14px;
}

.news-media {
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--home-border);
  color: var(--p-primary-600);
  font-size: 14px;

  &.news-media-dark {
    background-color: var(--p-primary-900);

    & img {
      height: 44px;
    }
  }
}

.news-body {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px 22px 24px;

  & h3 {
    font-size: 19px;
    line-height: 1.35;
  }

  & .strong-link {
    margin-top: auto;
    font-size: 15px;
  }
}

.news-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.news-meta {
  font-size: 13px;
  font-weight: 700;
  color: var(--home-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.news-text {
  font-size: 17px;
  white-space: pre-line;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-summary {
  color: var(--home-muted);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* What TSOSI does */
.missions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr));
  gap: var(--block-space);
}

.mission {
  display: flex;
  flex-direction: column;
  gap: 12px;

  & p {
    color: var(--home-muted);
  }
}

.mission-icon {
  height: 36px;
  width: auto;
  align-self: start;
  color: var(--home-link);
}

/* Call to action */
.cta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: clamp(28px, 5vw, 56px);
  border-radius: 20px;
  background-color: var(--home-accent);

  & h2 {
    font-size: clamp(26px, 2.8vw, 34px);
  }
}

.cta-text {
  flex: 1 1 420px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 18px;
}

/* Governance */
.governance-lead {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--block-space) 64px;
}

.governance-text {
  flex: 1 1 400px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: 16px;

  & > p {
    margin: 0;
    font-size: 17px;
    color: var(--home-muted);
  }
}

.lead-logos {
  flex: 1 1 480px;
  min-width: 0;
  justify-content: end;
  gap: 20px 48px;

  & .logo-link img {
    max-width: min(240px, 100%);
  }
}

.logo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px 28px;
}

.governance-members {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-top: 32px;
  border-top: 1px solid var(--home-border);

  & h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
  }
}

/* Logos shrink rather than wrap, wrapping only on narrow screens */
.member-logos {
  justify-content: space-between;
  flex-wrap: nowrap;
  column-gap: 32px;

  & .logo-link {
    min-width: 0;
    flex: 0 1 auto;
  }

  @media (max-width: 760px) {
    flex-wrap: wrap;
    justify-content: start;
  }
}

.logo-link {
  display: flex;
  align-items: center;
  border-radius: 4px;

  & img {
    display: block;
    width: auto;
    max-width: min(200px, 100%);
    object-fit: contain;
  }
}
</style>
