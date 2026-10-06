import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'category',
      label: 'Introduction',
      collapsed: false,
      items: [
        'intro/what-is-pipeline-kit',
        {
          type: 'doc',
          id: 'capabilities/modes',
          label: 'Two kits: pack and orchestrator',
        },
        'intro/problems',
        'intro/how-it-works',
        'intro/repo-layout',
        'intro/who-it-is-for',
      ],
    },
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: [
        'getting-started/prerequisites',
        'getting-started/install-cli',
        'getting-started/install-scopes',
        'getting-started/ide-adapters',
        'getting-started/first-project',
        'getting-started/first-workflow',
        'getting-started/checklist',
      ],
    },
    {
      type: 'category',
      label: 'Capabilities',
      items: [
        'capabilities/overview',
        {
          type: 'doc',
          id: 'capabilities/modes',
          label: 'Two kits',
        },
        'capabilities/extensions',
        'capabilities/workflows',
        'capabilities/planning-gates',
        'capabilities/knowledge',
        'capabilities/memory',
        'capabilities/plugins',
        'capabilities/graphify',
        'capabilities/archify',
        'capabilities/observability',
        'capabilities/telemetry',
        'capabilities/feature-flags',
        'capabilities/portal',
        'capabilities/wiki',
        'capabilities/loader',
      ],
    },
    {
      type: 'category',
      label: 'Workflows',
      items: [
        'workflows/ask',
        'workflows/feature-development',
        'workflows/jira',
        'workflows/github',
        'workflows/knowledge-bootstrap',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/agents-md',
        'guides/config',
        'guides/local-deploy',
        'guides/tests',
        'guides/gitignore',
        'guides/add-workflow',
        'guides/what-not-to-edit',
      ],
    },
    {
      type: 'category',
      label: 'Adapters',
      items: [
        'adapters/cursor',
        'adapters/claude-code',
        'adapters/github',
        'adapters/none',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/licensing',
        'reference/portal-protocol',
        'reference/config',
        'reference/pack-layout',
        'reference/agents',
        'reference/skills',
        'reference/document-standard',
      ],
    },
    {
      type: 'category',
      label: 'Troubleshooting',
      items: [
        'troubleshooting/index',
        'troubleshooting/jira-intake',
        'troubleshooting/slim-handoffs',
        'troubleshooting/interrupted-task',
        'troubleshooting/deploy-listeners',
        'troubleshooting/ui-copy',
        'troubleshooting/hooks',
        'troubleshooting/retro',
        'troubleshooting/test-layers',
        'troubleshooting/observability',
      ],
    },
    {
      type: 'category',
      label: 'Maintainers',
      items: [
        'maintainers/repo',
        'maintainers/authoring',
      ],
    },
  ],
};

export default sidebars;
