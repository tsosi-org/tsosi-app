# frontend

## Dev deps

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
npm install
```

- Run the dev server:

```bash
npm run dev
```

## Country data source

The static `country.json` file is a mix of the following sources:

* Country flags are downloaded from https://flagicons.lipis.dev
* Country centroïds are taken from https://github.com/gavinr/world-countries-centroids?tab=readme-ov-file

---

## Default content from vite setup
This template should help get you started developing with Vue 3 in Vite.

### Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

### Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

#### Type-Check, Compile and Minify for Production

```sh
npm run build
```

#### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
npm run test:unit
```

#### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
