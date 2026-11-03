# Fresh controlled runtime actions

These are board action sources for this run. They have not been executed on the board.
The caller first verifies and executes the newly prepared `live_common.py`, which supplies
`WORK`, `CFG`, dynamic board guards and manager helpers. The caller then verifies each
action source against its host manifest and executes it. No historical board guard or
WORK path is used.

## Files and interface

- `agent_helpers.py`: raw command output, kernel continuity checks, DPU/Top-5 checks,
  manager PID/starttime, inotify by FD, RSS, MemAvailable, slab and ZOCL samples.
- `action_sources/30_official_reload.py`: 30 official normal unload/load rounds; each
  round includes DPU query, identical ResNet18/image classification and sampling.
- `action_sources/40_sustained_inference.py`: at least 1800 monotonic seconds of
  synchronous identical-image inference, with 30-second samples by default.
- `action_sources/50_m3_functional.py`: official removal, M3 load and identical
  DPU/Top-5 checks. It does not access registers or PWM.
- `action_sources/60_restore.py`: inspect actual state, normal application removal,
  SIGINT candidate log flush, removal of the exact temporary drop-in, restoration
  of original manager and driver, official load and complete 26-file/Top-5 checks.

`CFG` must provide `work`, `boot_id`, `override`, `override_text_sha256`,
`stock_srcversion`, `fixed_srcversion`, `stock_hashes26`, `manager_sha256`,
`module_sha256`, and `agent_helpers_sha256`. Set `agent_helpers` to the helper's
absolute path under fresh WORK. `candidate_manager` and `candidate_module` identify
the exact previously board-tested staged binaries. Optional `candidate_log` defaults
to `WORK/candidate-manager.log`; `expected_watches` defaults to 5.
`sustained_seconds` defaults to 1800 and cannot be smaller; sampling interval defaults
to 30 seconds and must be greater than zero and no greater than 60 seconds.

The supplied common guard must support `guard(None, None)` while the driver is absent.
It must check actual boot/card/root/kernel, module reference/holders/DRM occupancy,
original file hashes (VART separately according to app), and actual active package.
`manager_guard(True)` verifies exact candidate executable and current state;
`manager_guard(False)` verifies original manager. Manager readiness uses SOCK_SEQPACKET.

## Evidence and failure behavior

Every phase creates a fresh `WORK/agent_logs/<phase>` directory and refuses reuse.
The complete stdout/stderr of each command, command/exit metadata, original dmesg,
incremental kernel review, samples and progress JSON remain there. Retrieve all files
to the Ubuntu evidence directory after execution; UART summaries alone are insufficient.
Long-phase progress remains in `40-sustained-inference/progress.json`.

Any unexpected return code, DPU or Top-5 difference, changed PID/watch count,
new kernel error or missing kernel continuity stops the action. There is no force unload
or automatic phase retry. Recovery verifies actual app/module/service/drop-in state and
does not overwrite original manager, client, module, firmware or configuration files.
The official manager's normal load must restore the original VART file bytes.
Candidate log errors are retained after SIGINT and do not prevent attempted recovery.
During recovery only, a new kernel diagnostic or lost kernel-log continuity is recorded
and baseline recovery continues through the remaining strict guards. Such diagnostics
or final candidate ERROR lines make the recovery phase's `passed` and `experiment_valid`
false even when `original_baseline_restored` is true. Unknown applications, changed
identity/hashes, busy DRM clients and failed normal unload commands still stop recovery.

The source helpers inspect the existing manager log between samples, but its unchanged
stdio buffering can delay ERROR lines. The final flushed candidate log must also be
reviewed. Finite RSS/slab observations do not prove absence of every memory leak; this
controlled one-image workload is not an FPS benchmark.
