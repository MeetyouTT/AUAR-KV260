# Vivado 2022.2 / Tcl 8.5. Usage: verify_skill.tcl NEW_OUT ?SKILL_OR_PROJECT_DIR?
# With no source argument, use the release RAR and checksum beside this script.
set release_dir [file dirname [file normalize [info script]]]

proc logged {command logfile} {
    if {[catch {exec {*}$command > $logfile 2>@1} why]} {
        error "Command failed: $command\n$why\nSee $logfile"
    }
}

proc verify_skill {args} {
    if {[llength $args] < 1 || [llength $args] > 2} {
        error "Usage: verify_skill.tcl NEW_OUT ?SKILL_OR_PROJECT_DIR?"
    }
    set out [file normalize [lindex $args 0]]
    if {[file exists $out]} {error "Choose a fresh output directory: $out"}
    set ::env(PYTHONDONTWRITEBYTECODE) 1
    set ::env(PYTHONIOENCODING) utf-8

    if {[llength $args] == 2} {
        set source [file normalize [lindex $args 1]]
        if {$out eq $source || [string first "$source/" "$out/"] == 0} {
            error "Output must be outside the source"
        }
        set skill $source
        if {![file isfile [file join $skill tests test_generator.py]]} {
            set skill [file join $source skill pynq-contract-testgen]
        }
        if {![file isfile [file join $skill scripts reproduce.py]]} {error "Skill not found: $skill"}
        file mkdir $out
    } else {
        set rar ""
        foreach name {unrar rar} {
            set cmd [auto_execok $name]
            if {[llength $cmd]} {set rar [lindex $cmd 0]; break}
        }
        if {$rar eq ""} {
            set rar [file join $::env(HOME) auar-engineering-delivery-XpV7MC rar-tool usr bin rar]
        }
        if {![file executable $rar]} {error "Use an installed rar/unrar, or pass the extracted Skill as the second argument"}
        cd $::release_dir
        set archive [file join $::release_dir auar_xuefei_board_enhanced.rar]
        if {![file isfile $archive] || ![file isfile archive.sha256]} {error "Release RAR or archive.sha256 is missing"}
        set extracted [file join $out source]
        file mkdir $extracted
        logged [list sha256sum -c archive.sha256] [file join $out archive-check.log]
        logged [list $rar x -idq $archive "$extracted/"] [file join $out extraction.log]
        set project [file join $extracted auar_xuefei]
        cd $project
        logged [list sha256sum --quiet -c checksums.sha256] [file join $out file-check.log]
        set skill [file join $project skill pynq-contract-testgen]
    }

    cd $skill
    puts "Running the original generator unit tests and mock IP cases in $out"
    logged [list python3 -B -m unittest discover -s tests -v] [file join $out unit_tests.log]
    logged [list python3 -B scripts/reproduce.py --out [file join $out mock]] [file join $out reproduce.log]

    # Read structured reports with the standard library already required by the Skill.
    set audit {
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1])
units = (out / "unit_tests.log").read_text()
if not re.search(r"^Ran 15 tests? in ", units, re.M) or units.rstrip().splitlines()[-1] != "OK":
    raise SystemExit("Unit test count or result differs; see unit_tests.log")
summary = json.loads((out / "mock/summary.json").read_text())
expected = {"adder": 36, "crc32": 37}
if (summary["status"] != "PASS" or summary["board_verified"] is not False or
        sorted((e["name"], e["cases"]) for e in summary["examples"]) != sorted(expected.items())):
    raise SystemExit("Unexpected mock summary; see mock/summary.json")
for row in summary["examples"]:
    report = json.loads((out / "mock" / row["name"] / "validation_report.json").read_text())
    if (row["returncode"] != 0 or row["status"] != "PASS" or report["status"] != "PASS" or
            report["mode"] != "mock" or report["hardware_executed"] is not False or report["board_verified"] is not False or
            len(report["cases"]) != expected[row["name"]] or any(c["status"] != "PASS" for c in report["cases"])):
        raise SystemExit("Failed example: " + row["name"])
receipt = {"status": "PASS", "unit_tests": 15, "mock_cases": expected, "mock_total": sum(expected.values()),
           "tcl": sys.argv[2], "python": summary["python"], "generator_sha256": summary["generator_sha256"],
           "board_verified": False}
(out / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("SKILL_TCL_PASS  unit=15  adder=36  crc32=37  mock_total=73")
}
    puts [exec python3 -B -c $audit $out [info patchlevel] 2>@1]
    puts "Receipt: [file join $out verification.json]"
}

if {[catch {verify_skill {*}$argv} message]} {
    puts stderr "SKILL_TCL_FAIL: $message"
    exit 1
}
exit 0

