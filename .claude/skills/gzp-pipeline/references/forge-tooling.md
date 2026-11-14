# Forge tooling

Every forge-side step in the other reference files (tracking issue, PR, assignment, labels, merge checks, merge, comments, closing issues) goes through **one** tool, chosen by config. This file covers how that choice is resolved and what each operation looks like on each tool. The reference files say "PR" and "issue" for both forges. Forgejo's pull requests and issues fill the same role at every step, and `Closes #<n>` in a PR body closes the issue on merge to the default branch on both forges.

## Resolve at activation

1. **Forge.** `gzp_forge` → `resolved.forge` (`github` | `forgejo`; unset → `github`). Read the `origin` remote with `git remote get-url origin` and record its host as `resolved.repo_host` (e.g. `github.com`, `codeberg.org`, `git.example.com`), plus `repo_owner`/`repo_name`. If the host clearly contradicts the forge (forge `github` but the host is `codeberg.org`, or forge `forgejo` but the host is `github.com`), stop and ask which is right. In an unattended run, report it as a blocker instead. A self-hosted host name proves nothing either way (GitHub Enterprise, self-hosted Forgejo), so don't flag it.
2. **Tool.** `gzp_forge_tool` → `resolved.forge_tool`:
   - `mcp`: the server named by `gzp_forge_mcp_name` must be connected in this session (its tools are in your tool list). Set `forge_cli` to null. MCP tool names differ per server (a GitHub MCP has `create_pull_request`, `pull_request_read`, `merge_pull_request`, `get_me`; a Forgejo MCP has its own names). Take them from that server's tool list, and never borrow another server's tool for the same job.
   - `cli`: set `forge_cli` to `gh` (GitHub) or `fj` (Forgejo, [forgejo-cli](https://codeberg.org/forgejo-contrib/forgejo-cli)). The CLI must be installed and authenticated against `repo_host`:
     - `gh`: `gh auth status --hostname <repo_host>` succeeds.
     - `fj`: `fj --version` runs, and `fj -H <repo_host> user view` prints your own profile (no username means "me"). Fix: `fj -H <repo_host> auth login`, or `auth add-token` on instances without OAuth.
   - unset (`auto`, configs from before 1.5.0 only): `mcp` when `gzp_forge_mcp_name` names a connected server, else `cli` when its check passes.
3. **Not usable → stop.** Say exactly which check failed, the fix (connect the MCP server, install/log in the CLI), and that `configure` can switch `gzp_forge_tool`. Don't quietly use the other tool, since the choice is the user's. In an unattended run this is a `blocked` report.

Write all four `resolved` fields with `uv run scripts/session_state.py set`.

## CLI rules

- **Never issue a command that waits for a person.** Commands that open `$EDITOR`, a browser, or an interactive prompt hang the pipeline. Always pass the body or message explicitly: `--body` on create, `--with-msg "<text>"` on `fj … close`, and a merge method on every merge. Never use `--web`. Never use `fj pr status --wait` either: in an interactive run, report pending checks and fall back to waiting at the merge gate; an unattended run returns.
- `fj` infers host and repo from the git remote. Pass `-H <repo_host>` (a global flag, placed before the subcommand) when it can't. Use `--repo owner/repo` or the `owner/repo#<n>` ID form when working a repo other than the current directory.
- Don't use `fj pr create --agit`. The pipeline always pushes a named branch (`{type}/{zoho-id}-gh{issue}-{slug}`), so the flow is identical on both forges and the branch carries the user's own GPG-signed commits.
- fj flags can change between releases. If a command below is rejected, check `fj <cmd> --help` and adapt. Never report a step as done when the command failed.

## Operation map

| Operation | `gh` (GitHub) | `fj` (Forgejo) |
| --- | --- | --- |
| Own identity (assignee login) | `gh api user --jq .login` | `fj user view` (own profile) |
| Existing labels | `gh label list` | not exposed by fj: reuse label names already seen on the repo's issues/PRs, or skip labeling |
| Search open issues by title (resume check) | `gh issue list --state open --search "<title> in:title"` | `fj issue search "<title>"`, then filter for open ones yourself |
| Create tracking / reported issue | `gh issue create --title "<t>" --body "<b>" --assignee @me [--label "<l>"]` | `fj issue create "<t>" --body "<b>"`, then `fj issue assign <n> <login>` and `fj issue edit <n> labels --add "<l>"` |
| Open PR | `gh pr create --base <base> --head <branch> --title "<t>" --body "<b>" --assignee @me [--label "<l>"]` | `fj pr create "<t>" --base <base> --head <branch> --body "<b>"`, then `fj pr assign --pr <n> <login>` (fj 0.7.0 takes the PR number through `--pr`, unlike `fj issue assign <n> <login>`) and `fj pr edit <n> labels --add "<l>"` |
| PR state, mergeability, checks | `gh pr view <n> --json state,mergedAt,mergeable,statusCheckRollup` | `fj pr view <n>` (state) and `fj pr status <n>` (mergeability + CI) |
| PR comments and reviews | `gh pr view <n> --comments`, plus `gh api repos/<owner>/<repo>/pulls/<n>/comments` for inline review comments | `fj pr view <n> comments`. If inline review comments aren't shown, say so in the close-out note; don't claim there are none |
| Merge (explicit method, delete branch) | `gh pr merge <n> --squash\|--merge\|--rebase --delete-branch` | `fj pr merge <n> --method <method> --delete`, using a method the repo allows (Forgejo: `merge`, `rebase`, `rebase-merge`, `squash`, `fast-forward-only`) |
| Close issue with a comment | `gh issue close <n> --comment "<why>"` | `fj issue close <n> --with-msg "<why>"` |
| Close PR unmerged | `gh pr close <n> --comment "<why>"` | `fj pr close <n> --with-msg "<why>"` |

With `mcp`, do the same operations with the connected server's equivalent tools. If that server has no tool for an operation (some Forgejo MCP servers can't merge or assign, for example), stop and report the gap, as in step 3 above. Don't switch to the CLI just for that one step.

The banned overrides apply to every tool: no `gh pr merge --admin`, no force-merge or force-push, no bypassing required checks or reviews.
