# Re-running review areas

Read by REVIEW when a checkpoint's areas are run again, or when an area a checkpoint skipped is run later.

A re-run of one or more areas is a new checkpoint, `n+1`, headed `### <n+1>. Re-run of checkpoint <n>: <areas>, <today>`. Running an area a checkpoint skipped is a re-run too. Dispatch only those areas into the new folder, and merge with `planner findings merge .planner/findings/<session id>/<n+1> --changed <paths> --areas FIN,REG`, naming them, with the same `Changed:` list. Areas not listed are neither read nor reported as did not run, and a file for one is ignored and listed under `ignored:`. The new findings get ids `F<n+1>.1` and on, so the ids of earlier checkpoints never change.
