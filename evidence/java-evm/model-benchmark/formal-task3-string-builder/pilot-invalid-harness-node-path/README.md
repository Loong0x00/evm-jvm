# Invalid task3 launch (excluded)

The parent stopped both launches after 105.8s on discovering that the benchmark wrapper still exported `NODE_PATH` from the canonical worktree instead of each pre-provisioned local candidate worktree. No candidate source edits/commits existed. The corrected wrapper now derives NODE_PATH from `cwd`.

This launch also exposed a second-signal cleanup bug: tmux SIGHUP could interrupt the wrapper while it was already terminating the Pi process group. Signal handlers now ignore further wrapper signals during group cleanup. Raw partial metrics and wrapper diagnostics are preserved and excluded from comparison/selection. No child process remained.
