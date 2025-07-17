import pluginVitest from '@vitest/eslint-plugin'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import pluginImport from "eslint-plugin-import"
import pluginVue from 'eslint-plugin-vue'


export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**'],
  },

  ...pluginVue.configs['flat/essential'],
  ...vueTsEslintConfig(),
  
  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  skipFormatting,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "off"
    },
  },
  {
    plugins: {
      import: pluginImport
    },
    rules: {
      'import/newline-after-import': ['error', { 'count': 2 }],
      'import/order': [
        'error',
        {
          groups: [
            ["builtin", "external"], 
            ["internal"],
            ["parent"],
            ["sibling", "index"],
          ],
          'newlines-between': 'always',   // Adds a newline between import groups
        }
      ]
    }
  }
]
