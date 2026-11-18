# **GIT CONVENTIONS AND STANDARDS**

# **1\. Git flow**

[Cheatsheet](https://danielkummer.github.io/git-flow-cheatsheet/)

Importance branches:

| Name           | Description                              |
|:---------------|:-----------------------------------------|
| master         | latest release code                      |
| develop        | in development code                      |
| testing        | development and testing environment code |
| staging        | staging environment code                 |
| production     | production environment code              |
| release/vX.X.X | release code by versions                 |

# **2\. Branch name**

template: *{phase}/{group}/\#{issue-id}-{name}*  
example:

* *p2.5/feat/\#3-authentication* \[implement the authentication feature with the issue id of 3\]
* *p2.5/conf/update-access-token-lifetime* \[config API access token lifetime without an issue id\]

* **phase**: the project phase identifier (e.g. `p1`, `p2.5`). See **Section 5** for details.

* **group**:   
  choose whichever group that matches in the following

| Name   | Description         |
|:-------|:--------------------|
| feat   | feature code        |
| fix    | bug fix code        |
| hotfix | hotfix code         |
| ref    | refactor code       |
| test   | unit test code      |
| conf   | configuration code  |
| chore  | other kinds of code |

* **issue-id**: the related issue’s id on the task management tool (Backlog), usually is an integer. Can be skipped if
  there is no related issue.
* **name**: a descriptive name for the branch. Space must be replaced with *"-"*

# **3\. Pull request**

* Must not create a large pull request. Prefer multiple pull requests with few changes over one pull request with a lot
  of changes
* Must provide setup instructions for the PR-ed code in the comment when necessary (add new dependencies, update master
  data, …)

# **4\. Commit message**

Follow the below guidance when writing commit messages. This guidance can also be shared with LLM to help you write
commit messages.

```
Write a git commit message in the following format:
 [type]: [Short summary in sentence case]
 
 - [Bullet point 1: Describe the main change, referencing files or modules if relevant.]
 - [Bullet point 2: List any additional changes, improvements, or fixes.]
 - [Bullet point 3: Mention any documentation updates, dependency changes, or clarifications.]
 
 Commit types:
 feat: feature code
 fix: bug fix code
 hotfix: hotfix code
 ref: refactor code
 test: unit test code
 conf: configuration code
 chore: other kinds of code
 doc: documentation
 
 Guidelines:
 Use the correct commit type.
 Keep the summary concise and in sentence case.
 Use clear, specific bullet points for each change.
 Reference files, modules, or dependencies when relevant.
 Avoid overly verbose descriptions or unnecessary details.
 Do not include unrelated changes in the same commit message.
 
 Example:
 chore: Update queue config to use Redis and revise README
 
 - Set the default queue connection to `redis` in `queue.php`.
 - Update system requirements and dependencies in README for Laravel 12, PHP 8.3, Postgres 17, and Redis 7.
 - Fix typos and improve phrasing for clarity.
```

# **5\. Multiple phases project**

If the project consists of multiple phases, each phase related to development code should be organized into a directory.
For example, phase 1 will have the following branches:

* **p1/develop**: as the merge branch for all in development code
* **p1/feat/\#1-login**: as the development branch for the login feature
* **p1/fix/\#2-failed-to-login**: as the fix branch for the failed to login error

# **6\. Hotfixes and minor changes**

All hotfixes and minor changes ordered by the client in a day should be organized into a directory. The directory will
be named in the **yyyymmdd** format to indicate which date the changes were ordered by the client and developed. For
example, hotfixes and minor changes ordered in 20/04/2024 will be organized as follows:

* **20240420/conf/\#10-extend-session-time**: as the branch to configure session lifetime
* **20240420/hotfix/\#11-unable-to-update-password**: as the branch to fix the unable to update password error
