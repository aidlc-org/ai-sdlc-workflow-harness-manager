import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Pipeline Kit',
  tagline: 'A portable operating model for coding agents',
  favicon: 'img/logo.svg',

  future: {
    v4: true,
  },

  url: 'http://127.0.0.1:3000',
  baseUrl: '/',

  onBrokenLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  themes: [
    '@docusaurus/theme-mermaid',
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['en'],
        indexBlog: false,
        docsRouteBasePath: '/docs',
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/logo.svg',
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'Pipeline Kit',
      logo: {
        alt: 'Pipeline Kit',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/getting-started/install-cli',
          label: 'Install',
          position: 'left',
        },
        {
          to: '/docs/components/overview',
          label: 'Components',
          position: 'left',
        },
        {
          to: '/docs/cookbooks/',
          label: 'Cookbooks',
          position: 'left',
        },
        {
          to: '/docs/reference/cli',
          label: 'CLI',
          position: 'left',
        },
        {
          type: 'search',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Start',
          items: [
            {label: 'What is Pipeline Kit', to: '/docs/intro/what-is-pipeline-kit'},
            {label: 'Problems we solve', to: '/docs/intro/problems'},
            {label: 'Install', to: '/docs/getting-started/install-cli'},
            {label: 'First project', to: '/docs/getting-started/first-project'},
          ],
        },
        {
          title: 'Components',
          items: [
            {label: 'Overview', to: '/docs/components/overview'},
            {label: 'Packages', to: '/docs/components/packages'},
            {label: 'Plugins', to: '/docs/capabilities/plugins'},
            {label: 'Governance', to: '/docs/components/governance'},
          ],
        },
        {
          title: 'Cookbooks',
          items: [
            {label: 'All cookbooks', to: '/docs/cookbooks/'},
            {label: 'First feature', to: '/docs/cookbooks/first-feature'},
            {label: 'Add a workflow', to: '/docs/cookbooks/add-workflow'},
            {label: 'Enterprise governance', to: '/docs/cookbooks/enterprise-governance'},
          ],
        },
        {
          title: 'Reference',
          items: [
            {label: 'CLI', to: '/docs/reference/cli'},
            {label: 'config.json', to: '/docs/reference/config'},
            {label: 'Troubleshooting', to: '/docs/troubleshooting'},
            {label: 'Maintainers', to: '/docs/maintainers/repo'},
          ],
        },
      ],
      copyright: `Pipeline Kit documentation. Preview locally with npm start.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
