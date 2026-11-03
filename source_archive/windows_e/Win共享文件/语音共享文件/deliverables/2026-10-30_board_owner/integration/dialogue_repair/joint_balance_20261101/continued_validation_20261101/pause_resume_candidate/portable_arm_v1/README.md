Portable public validation for explicit pause/continue
====================================================

Run from this extracted package with Python 3.9 or newer:

    python3 -I -B run_public_validation.py

The runner checks all pinned inputs before and after running exactly the existing
nine public tests. The package is stdlib-only; it opens no microphone, camera,
network connection, model, service, or private database. It does not deploy or
change the running application. Device testing must remain under the existing
device owner's control, with the application paused as arranged by that owner.

before/tools/voice_first_recording.py is the unchanged 5737 baseline.
after/tools/voice_first_recording.py is the unchanged 54fa candidate.
support/ contains the seven unchanged pinned dependency sources. Their selected
definitions are AST-loaded with postponed annotations; production modules are
not imported. Capture, visual, and preference backends are public stand-ins.

original_test_public_methods.py is the unchanged original test source, retained
for review. Execute test_public_methods_portable.py only through the runner.
Its only adaptations are the package-relative pinned source loader and output
result filename. All original test, fixture, and AST definition method bodies
are unchanged. Temporary public selection files are created below this package
and cleaned up by the existing test fixture. No real selection or storage paths
are read or written.

New output files are PORTABLE_TEST_RESULT.json and PORTABLE_RUN_RECEIPT.json.
They are run receipts and are not frozen input pins. Save them with the actual
device metadata before re-running. An AMD64 local pass is not an ARM pass, and
an ARM public-test pass is not real conversation or deployment acceptance.

The manifest and zip digest supplied by the coordinator identify the package.
This package contains no deployment command, model data, virtual environment,
or private conversation data. Do not overwrite the original candidate evidence.
