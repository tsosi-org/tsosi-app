Welcome to the front-end application of TSOSI, built with [Vue.js](https://vuejs.org/guide/introduction.html) and [PrimeVue](https://primevue.org/) (components library).
We additionally use:

- [Leaflet](https://leafletjs.com/) for maps
- Chart.js for charts, with [built-in handlers](https://primevue.org/chart/) in PrimeVue.

# Install Dev dependencies

**ONLY WHEN NOT USING THE DEVCONTAIENR**

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

The different routes are defined [here](./src/router/index.ts).
We have only 4 pages as of 2025-07-07:

- [Home page](./src/views/HomeView.vue)
- [Static pages](./src/views/StaticContentView.vue) - If more static pages appear, we should think of migrating to Nuxt.js to handle that properly (built-in feature).
- [Entity pages](./src/views/EntityView.vue) - The core of the application, individual entity page showing metadata and listing transfers.
- [Transfer pages](./src/views/TransferView.vue) - Individual transfer page.

## [Ref-data](./src/singletons/ref-data.ts)

As of now (2025-07-07), we fetch the referential data on the application startup, that is then used throughout the app.
This includes:

- Currency data - All the currencies referenced in TSOSI transfers.
- Country data - A static list of all the country codes, names and icons.
- Entity data - The list of all entities in TSOSI database with basic metadata: primary ID, name, identifiers and image link.

  **TODO**: This must be watched when the entity dataset grows as it might slow down the app.

## [Components](./src/components/)

I tried a bit to follow a bit the atomic design pattern to create and order components:

- [Atoms](./src/components/atoms/) - Contains low-level components, such as button, image or link
- Everythin else is not structured and can use any atoms or other non-atomic components :)

## Styling

This could and should be reworked for a more professional and consistent approach, for example by following the PrimeVue [theming idiom](https://primevue.org/theming/styled/) that declares CSS variables for component, that can be set globally in PrimeVue config or modified per component instance ("Design tokens", passed as `:dt="{my_tokens}"`).

Additionally, one could use a CSS utility framework such as Tailwind to replace CSS by HTML classes.

Currently, each component has scoped styles for everything it defines.
Shared styles are put in [base.css](./src/assets/css/base.css) or [main.css](./src/assets/css/main.css).

## Data handling

As much as possible, data components are abstracted to work with any data type (example: [TableComponent](./src/components/TableComponent.vue) or [SummaryComponent](./src/components/SummaryComponent.vue)).
The goal is to pass a "config" object to the component that indicates how to retrive the data and how to process it, mainly according to the data type.
See [data.utils.ts](./src/utils/data-utils.ts).

## Icons - Font Awesome

We use icons from [Font Awesome free icons](https://fontawesome.com/search?ic=free), installed with dedicated vue libraries (`@fortawersome` something in [package.json](./package.json)).

To use a "new" icon, it must be imported in [main.ts](./src/main.ts) and registered in `usedIcons`.
Then you can use it in templates with the default array syntax:

```html
<font-awesome-icon :icon="['fas', 'house']" />
```

## Country data source

The static `country.json` file is a mix of the following sources:

- Country flags are downloaded from https://flagicons.lipis.dev
- Country centroïds are taken from https://github.com/gavinr/world-countries-centroids?tab=readme-ov-file
