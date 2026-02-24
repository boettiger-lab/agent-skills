# agent-skills

Providing appropriate context and knowledge our agents need to succeed.  

[Agent skills](https://agentskills.io/home)


## Working with Claude Code (via CLI or VSCode)

Clone to `~/.claude/skills`: 

```bash
git clone https://github.com/boettiger-lab/agent-skills ~/.claude/skills
```

Other clients can be instructed to load these skills on demand by having the model copy their metadata into AGENTS.md or similar.

###  When working with devcontainers

symlink the skills dir, e.g.

```bash
{
  // ... your existing devcontainer config ...
  
  "mounts": [
    "source=${localEnv:HOME}${localEnv:USERPROFILE}/.claude/skills,target=/home/vscode/.claude/skills,type=bind,consistency=cached"
  ]
}
```



