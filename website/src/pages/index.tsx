import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

type Mode = 'kit' | 'orchestrator';

const kitCommand = `uv tool install git+<repo-url>
cd /path/to/your-app
pipeline-kit init --ide cursor
pipeline-kit doctor --ide cursor`;

const orchestratorCommand = `uv tool install -e ".[orchestrator]"
cd /path/to/your-app
pipeline-kit init --mode orchestrator --ide cursor
pipeline-kit run --slug preview --workflow feature-development --dry-run`;

const challenges = [
  {
    id: 'context',
    title: 'Context explosion',
    factory: 'Every specialist prompt, wiki page, and skill sits in the IDE folder. The model reads the whole factory on every turn.',
    value: 'Process lives in .pipeline. The IDE discovers one skill. Each step gets an allowlist, not the pack.',
  },
  {
    id: 'models',
    title: 'Wrong model for the work',
    factory: 'Planning, review, and implementation all run on the same coding model. Cost goes up. Quality does not.',
    value: 'Jev classifies the step, then picks from a shortlist. Opus or GPT for reasoning. Composer for implementation.',
  },
  {
    id: 'ide',
    title: 'Process glued to one IDE',
    factory: 'Moving from Cursor to Claude Code means copying and rewriting the tree. The factory cannot leave the editor.',
    value: 'Thin adapters. Cursor, Claude Code, GitHub, or none. The pack and the wheel stay the same.',
  },
  {
    id: 'leak',
    title: 'Customer leakage',
    factory: 'Ports, Jira keys, and folder names are baked into skills. The next engagement cannot reuse the factory.',
    value: 'Engagement overlay is config.json. Skills stay generic. Take the kit to the next customer.',
  },
  {
    id: 'ladder',
    title: 'One ladder for every ask',
    factory: 'A taxonomy question starts PM → BA → developer. A bug runs a full feature plan.',
    value: 'Named workflows. ask stays a question. feature-development delivers. jira-bug skips planning.',
  },
];

const controls = [
  {
    id: 'classifier',
    kicker: 'Orchestrator',
    title: 'Model classifier',
    line: 'Pick the Cursor model from what the agent must do, not from habit.',
    body: 'Jev sees a shortlist — Composer, Grok, Claude Opus, GPT — with a per-agent fit line. Planning and review mark Composer poor fit. Implementation marks it good. Add a model in candidates or cards, not both. A pin skips Jev for one step.',
    to: '/docs/capabilities/modes',
  },
  {
    id: 'knowledge',
    kicker: 'Opt-in',
    title: 'Knowledge',
    line: 'QA design from a real code graph, then a human promote.',
    body: 'knowledge init does not run Graphify for you. Extract writes graphify-out/graph.json. Architects add a model delta. Testers get cases.json and a Playwright projector. The feature ladder stays unchanged until the flag is on.',
    to: '/docs/capabilities/knowledge',
  },
  {
    id: 'plugins',
    kicker: 'Opt-in',
    title: 'Plugins',
    line: 'Graphify and Archify stay off until you install them.',
    body: 'plugins install graphify registers the official CLI skill. plugins install archify pins Archify v2.16.0 for interactive architecture HTML. Init never turns these on. Mermaid in architecture.md stays required.',
    to: '/docs/capabilities/plugins',
  },
  {
    id: 'obs',
    kicker: 'Bundled add-on',
    title: 'Observability',
    line: 'Trace what the coding agent did, not the customer app.',
    body: 'obs install merges hooks into a local ledger, then Langfuse. Scores are deterministic. Distinct from product telemetry-agent. Not an entry in plugins list.',
    to: '/docs/capabilities/observability',
  },
];

const agents = [
  {
    id: 'pm',
    label: 'Product manager',
    need: 'Planning — requirements and acceptance criteria',
    pick: 'claude-opus-5',
    why: 'Reasoning. Composer is a poor fit.',
  },
  {
    id: 'arch',
    label: 'Architect',
    need: 'Architecture — boundaries and tradeoffs',
    pick: 'gpt-5.5',
    why: 'Reasoning. Composer is a poor fit.',
  },
  {
    id: 'dev',
    label: 'Developer',
    need: 'Implementation — edit code and fix defects',
    pick: 'composer-2.5',
    why: 'Fast coding. Opus is heavier than needed.',
  },
  {
    id: 'critic',
    label: 'Critic',
    need: 'Review — gaps and missing criteria',
    pick: 'claude-opus-5',
    why: 'Reasoning. Composer is a poor fit.',
  },
  {
    id: 'tester',
    label: 'Tester',
    need: 'Verification — follow tests and inspect code',
    pick: 'composer-2.5',
    why: 'Fast coding. Prefer Composer.',
  },
];

function CopyButton({text}: {text: string}): ReactNode {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className={styles.ghost}
      onClick={() => {
        if (!navigator.clipboard) {
          return;
        }
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1400);
        });
      }}>
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

function useMotion() {
  const [reduce, setReduce] = useState(false);
  const [progress, setProgress] = useState(0);
  const [shift, setShift] = useState(0);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReduce(media.matches);
    sync();
    media.addEventListener('change', sync);
    return () => media.removeEventListener('change', sync);
  }, []);

  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? window.scrollY / max : 0);
      setShift(Math.min(window.scrollY, 520));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, {passive: true});
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const nodes = document.querySelectorAll('[data-reveal]');
    if (!nodes.length) {
      return undefined;
    }
    if (reduce) {
      nodes.forEach((node) => node.classList.add(styles.seen));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add(styles.seen);
          }
        });
      },
      {threshold: 0.14, rootMargin: '0px 0px -8% 0px'},
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [reduce]);

  return {reduce, progress, shift};
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const {reduce, progress, shift} = useMotion();
  const [mode, setMode] = useState<Mode>('kit');
  const [challengeId, setChallengeId] = useState(challenges[0].id);
  const [controlId, setControlId] = useState(controls[0].id);
  const [agentId, setAgentId] = useState(agents[0].id);
  const command = mode === 'kit' ? kitCommand : orchestratorCommand;
  const challenge = challenges.find((item) => item.id === challengeId) ?? challenges[0];
  const control = controls.find((item) => item.id === controlId) ?? controls[0];
  const agent = agents.find((item) => item.id === agentId) ?? agents[0];

  useEffect(() => {
    document.documentElement.classList.add('pk-foundry');
    return () => document.documentElement.classList.remove('pk-foundry');
  }, []);

  useEffect(() => {
    const rows = challenges
      .map((item) => document.getElementById(`challenge-${item.id}`))
      .filter((node): node is HTMLElement => Boolean(node));
    if (!rows.length) {
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const hit = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
        const id = hit?.target.getAttribute('data-id');
        if (id) {
          setChallengeId(id);
        }
      },
      {rootMargin: '-35% 0px -45% 0px', threshold: [0.4, 0.7]},
    );
    rows.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  return (
    <Layout
      title={`${siteConfig.title}`}
      description="An operating model for enterprise agent factories. Repeatable process, the right model per step, opt-in knowledge and plugins.">
      <div className={styles.page}>
        <div className={styles.progress} style={{transform: `scaleX(${progress})`}} />

        <header className={styles.hero}>
          <div
            className={styles.bloom}
            style={reduce ? undefined : {transform: `translate3d(0, ${shift * 0.18}px, 0)`}}
          />
          <div className={styles.heroInner}>
            <p className={styles.kicker}>Pipeline Kit</p>
            <Heading as="h1" className={styles.heroTitle}>
              An operating model
              <br />
              for agent factories.
            </Heading>
            <p className={styles.heroLead}>
              Enterprise teams already have coding agents. They do not have a
              repeatable factory: the right workflow, the right model, and a
              pack that survives the next customer. Pipeline Kit is that
              operating model.
            </p>
            <div className={styles.actions}>
              <Link className={styles.primary} to="/docs/getting-started/install-cli">
                Install the CLI
              </Link>
              <Link className={styles.textLink} to="/docs/cookbooks/first-feature">
                First feature cookbook
              </Link>
              <button type="button" className={styles.textLink} onClick={() => document.getElementById('factory')?.scrollIntoView({behavior: reduce ? 'auto' : 'smooth'})}>
                See the factory problems
              </button>
            </div>
          </div>
        </header>

        <section className={styles.value} data-reveal>
          <div className={styles.shell}>
            <p>Same process on every engagement. Overlay the customer in config, not in skills.</p>
            <p>Classify the step, then pick the model. Reasoning models plan. Coding models implement.</p>
            <p>Knowledge, plugins, and traces stay opt-in. The core pack stays portable.</p>
          </div>
        </section>

        <section id="factory" className={styles.section}>
          <div className={styles.shell}>
            <header className={styles.head} data-reveal>
              <p className={styles.kicker}>Enterprise factories</p>
              <Heading as="h2">The work is not “add another agent.”</Heading>
              <p>
                The work is making agents behave like a plant: one procedure,
                measured cost, and a model that matches the station. Scroll the
                left column. The answer stays pinned.
              </p>
            </header>
            <div className={styles.pin}>
              <div>
                {challenges.map((item) => (
                  <button
                    key={item.id}
                    id={`challenge-${item.id}`}
                    data-id={item.id}
                    type="button"
                    className={clsx(styles.row, challengeId === item.id && styles.rowOn)}
                    onClick={() => setChallengeId(item.id)}>
                    <span>{item.title}</span>
                    <em>{item.factory}</em>
                  </button>
                ))}
              </div>
              <aside className={styles.sticky} data-reveal>
                <p className={styles.kicker}>What the kit does</p>
                <h3>{challenge.title}</h3>
                <p>{challenge.value}</p>
                <Link to="/docs/intro/problems">Full problem statement</Link>
              </aside>
            </div>
          </div>
        </section>

        <section className={styles.section} id="controls">
          <div className={styles.shell}>
            <header className={styles.head} data-reveal>
              <p className={styles.kicker}>Factory controls</p>
              <Heading as="h2">Four things that change how the plant runs.</Heading>
              <p>
                Not a catalog of features. These are the controls operators
                actually turn: which model, which knowledge, which plugin, and
                whether the run is scored.
              </p>
            </header>
            <div className={styles.pin}>
              <div>
                {controls.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={clsx(styles.row, controlId === item.id && styles.rowOn)}
                    onClick={() => setControlId(item.id)}>
                    <span>
                      <small>{item.kicker}</small>
                      {item.title}
                    </span>
                    <em>{item.line}</em>
                  </button>
                ))}
              </div>
              <aside className={styles.sticky} data-reveal>
                <p className={styles.kicker}>{control.kicker}</p>
                <h3>{control.title}</h3>
                <p>{control.body}</p>
                <Link to={control.to}>Open the docs</Link>
              </aside>
            </div>
          </div>
        </section>

        <section className={styles.section} id="classifier">
          <div className={styles.shell}>
            <header className={styles.head} data-reveal>
              <p className={styles.kicker}>Model classifier</p>
              <Heading as="h2">Each station gets a model that fits the work.</Heading>
              <p>
                Jev does not invent the next agent. The sealed graph does that.
                Jev only answers: which Cursor model should run this step.
              </p>
            </header>
            <div className={styles.classify} data-reveal>
              <div className={styles.stations}>
                {agents.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={clsx(styles.station, agentId === item.id && styles.stationOn)}
                    onClick={() => setAgentId(item.id)}>
                    <span>{item.label}</span>
                    <code>{item.pick}</code>
                  </button>
                ))}
              </div>
              <div className={styles.decision}>
                <p className={styles.kicker}>This step</p>
                <h3>{agent.label}</h3>
                <p>{agent.need}</p>
                <p className={styles.pick}>
                  Runs <code>{agent.pick}</code>
                </p>
                <p>{agent.why}</p>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.section} id="runtimes">
          <div className={styles.shell}>
            <header className={styles.head} data-reveal>
              <p className={styles.kicker}>Two runtimes</p>
              <Heading as="h2">Same workflow names. Pick one surface.</Heading>
            </header>
            <div className={styles.runtimes} data-reveal>
              <div>
                <p className={styles.kicker}>Kit mode — default</p>
                <h3>Markdown pack</h3>
                <p>
                  Skills, briefs, and the loader live in <code>.pipeline</code>.
                  The IDE only exposes <code>run-workflow</code>. This is what
                  most engagements should use.
                </p>
              </div>
              <div>
                <p className={styles.kicker}>Orchestrator mode</p>
                <h3>Python engine</h3>
                <p>
                  Sealed graph. Drive it with <code>run</code>, <code>approve</code>,
                  and <code>resume</code>. Pass <code>--request</code>. Jev
                  classifies the model before each agent.
                </p>
              </div>
            </div>
            <div className={styles.terminal} data-reveal>
              <div className={styles.terminalBar}>
                <div className={styles.switch} role="tablist" aria-label="Runtime">
                  <button type="button" className={clsx(mode === 'kit' && styles.on)} onClick={() => setMode('kit')}>
                    Kit
                  </button>
                  <button type="button" className={clsx(mode === 'orchestrator' && styles.on)} onClick={() => setMode('orchestrator')}>
                    Orchestrator
                  </button>
                </div>
                <CopyButton text={command} />
              </div>
              <pre>
                <code>{command}</code>
              </pre>
            </div>
            <p className={styles.foot}>
              <Link to="/docs/capabilities/modes">Compare the two kits</Link>
              {' · '}
              <Link to="/docs/components/overview">Components</Link>
              {' · '}
              <Link to="/docs/cookbooks/">Cookbooks</Link>
              {' · '}
              <Link to="/docs/getting-started/install-cli">Install</Link>
            </p>
          </div>
        </section>

        <section className={styles.section} id="enterprise">
          <div className={styles.shell}>
            <header className={styles.head} data-reveal>
              <p className={styles.kicker}>Subscription</p>
              <Heading as="h2">What an org license covers.</Heading>
              <p>
                Install stays open. One license turns on the controls a delivery
                org runs across engagements.
              </p>
            </header>
            <div className={styles.runtimes} data-reveal>
              <div>
                <p className={styles.kicker}>Included</p>
                <h3>The factory</h3>
                <p>
                  Kit mode, <code>ask</code>, and <code>feature-development</code>.
                  Loader, wiki, planning gates, and policy hooks. Install, doctor,
                  and the workflow list stay open.
                </p>
              </div>
              <div>
                <p className={styles.kicker}>Org license</p>
                <h3>Four paid areas</h3>
                <ul className={styles.offer}>
                  <li>
                    <Link to="/docs/capabilities/modes">Orchestrator and the model classifier.</Link>{' '}
                    Sealed graph, approve, and resume.
                  </li>
                  <li>
                    <Link to="/docs/workflows/jira">Jira intake.</Link>{' '}
                    Story, epic, and bug workflows.
                  </li>
                  <li>
                    <Link to="/docs/capabilities/extensions">Governance workflows.</Link>{' '}
                    Security, CI, dependency, and accessibility review.
                  </li>
                  <li>
                    <Link to="/docs/capabilities/observability">Observability and eval.</Link>{' '}
                    Traces, scores, and cost. Local report stays open.
                  </li>
                </ul>
              </div>
            </div>
            <p className={styles.foot}>
              One license covers every engagement on the machine. Activate with{' '}
              <code>pipeline-kit license activate</code>
              {' · '}
              <Link to="/docs/cookbooks/enterprise-governance">Governance cookbook</Link>
              {' · '}
              <Link to="/docs/components/governance">Governance hub</Link>
            </p>
          </div>
        </section>
      </div>
    </Layout>
  );
}
