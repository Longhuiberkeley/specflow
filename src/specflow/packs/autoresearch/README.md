# Autoresearch Pack

Autonomous research loop for SpecFlow. Runs iterative experiments against a defined competition (dataset + metric + verify command), producing structured EXPT artifacts and condensed FIND artifacts that survive context rot.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch), adapted from [autoresearch_fork](https://github.com/Longhuiberkeley/autoresearch_fork) which builds on [Claude Autoresearch](https://github.com/uditgoenka/autoresearch).

## Coverage

- 4 new artifact types: `competition`, `loop`, `experiment`, `finding`
- 1 skill: `specflow-autoresearch` (run, plan, review, leaderboard subcommands)
- 4 reference protocols: autonomous loop, competition setup, explore/exploit modes, finding generation

## Usage

```bash
specflow init --preset autoresearch
```

Then invoke `/specflow-autoresearch` in your AI assistant to start a research loop.
