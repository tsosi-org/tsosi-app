Welcome to the front-end application of TSOSI, built with [Vue.js](https://vuejs.org/guide/introduction.html) and [PrimeVue](https://primevue.org/) (components library).
We additionally use:

- [Leaflet](https://leafletjs.com/) for maps
- Chart.js for charts, with [built-in handlers](https://primevue.org/chart/) in PrimeVue.

# Install Dev dependencies

**ONLY WHEN NOT USING THE DEVCONTAINER**

- Install Node.js & NPM, using NVM:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install 24
node -v # Output v24.x.0
nvm current # Output v24.x.0
npm -v # Output 11.x.0
```

- Install dependencies:

```bash
# In frontend/ directory
npm ci
```

- Run the dev server:

```bash
npm run dev
```

# Vue.js app - Intro

## [Views](./src/views/)

The different routes are defined [here](./src/router/index.ts):

- `/` - [Home page](./src/views/HomeView.vue)
- `/explore` - [Entity list](./src/views/EntityListView.vue) - Browse and filter all entities (`/entities` redirects here).
- `/entities/:id` - [Entity pages](./src/views/EntityView.vue) - The core of the application, individual entity page showing metadata and listing transfers.
- `/transfers/:id` - [Transfer pages](./src/views/TransferView.vue) - Individual transfer page.
- `/provide` - [Provide data](./src/views/ProvideView.vue) - Embeds a Grist form for data providers, prefilled with the `name` and `ror_url` query parameters.
- `/pages/*` - Static pages: [FAQ](./src/views/FaqView.vue), [About](./src/views/AboutView.vue), [Legal notice](./src/views/LegalNotices.vue), [Privacy policy](./src/views/PrivacyPolicyView.vue), [Newsletter](./src/views/NewsView.vue) and [Blog](./src/views/BlogView.vue) (list and individual posts).
- Any other path - [Not found page](./src/views/NotFoundView.vue).

Static pages wrap their content in the [StaticContentView](./src/views/StaticContentView.vue) layout component (it is not a route itself).
[DevModeView](./src/views/DevModeView.vue) enables the dev mode flag, but its route is currently disabled.

## [Ref-data](./src/singletons/ref-data.ts)

We fetch the referential data on the application startup, that is then used throughout the app.
This includes:

- Currency data - All the currencies referenced in TSOSI transfers.
- Country data - A static list of all the country codes, names and icons.
- Entity data - The list of all entities in TSOSI database with basic metadata: primary ID, name, identifiers and image link.

  **TODO**: This must be watched when the entity dataset grows as it might slow down the app.

Other app-wide state lives in [singletons](./src/singletons/): the selected display currency (`currencyStore.ts`), the dev mode flag (`devMode.ts`) and the home page big-header state (`fixedHeaderStore.ts`).

## [Components](./src/components/)

Components loosely follow the atomic design pattern:

- [Atoms](./src/components/atoms/) - Contains low-level components, such as button, image or link
- Everything else is not structured and can use any atoms or other non-atomic components :)

## Styling

This could and should be reworked for a more professional and consistent approach, for example by following the PrimeVue [theming idiom](https://primevue.org/theming/styled/) that declares CSS variables for component, that can be set globally in PrimeVue config or modified per component instance ("Design tokens", passed as `:dt="{my_tokens}"`).

Additionally, one could use a CSS utility framework such as Tailwind to replace CSS by HTML classes.

Currently, each component has scoped styles for everything it defines.
Shared styles are put in [base.css](./src/assets/css/base.css) or [main.css](./src/assets/css/main.css).

## Data handling

As much as possible, data components are abstracted to work with any data type (example: [TableComponent](./src/components/TableComponent.vue) or [SummaryComponent](./src/components/SummaryComponent.vue)).
The goal is to pass a "config" object to the component that indicates how to retrieve the data and how to process it, mainly according to the data type.
See [data-utils.ts](./src/utils/data-utils.ts).

## Icons - Font Awesome

We use icons from [Font Awesome free icons](https://fontawesome.com/search?ic=free), installed with dedicated vue libraries (the `@fortawesome/*` packages in [package.json](./package.json)).

To use a "new" icon, it must be imported in [main.ts](./src/main.ts) and registered in `usedIcons`.
Then you can use it in templates with the default array syntax:

```html
<font-awesome-icon :icon="['fas', 'house']" />
```

## Country data source

The static `country.json` file is a mix of the following sources:

- Country flags are downloaded from https://flagicons.lipis.dev
- Country centroïds are taken from https://github.com/gavinr/world-countries-centroids?tab=readme-ov-file
