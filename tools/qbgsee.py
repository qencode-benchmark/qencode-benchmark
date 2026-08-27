#!/usr/bin/env python
"""Interoperate with the DARPA Quantum Benchmarking GSEE benchmark.

The QB-GSEE benchmark (https://github.com/isi-usc-edu/qb-gsee-benchmark) defines a
problem-instance format and a solution format for ground-state energy estimation. QEncode
produces exactly the quantities a QB-GSEE solution wants -- an energy in Hartree, an error
bound, logical qubit and T-gate counts, run times and a digital signature -- so a certified
entry can be expressed as a QB-GSEE solution without recomputing anything.

Two subcommands:

  compare   which QEncode molecules correspond to QB-GSEE problem instances, and whether
            the published gaps meet the QB-GSEE accuracy requirement, which is chemical
            accuracy (1.59 mHa) rather than QEncode's looser 10 mHa certification bar.

  export    render a QEncode entry as a QB-GSEE solution.json against a named problem
            instance, and validate it against the published schema.

Everything here reads; nothing modifies an entry or a hash.

    python tools/qbgsee.py compare
    python tools/qbgsee.py export releases/v4/db/<entry>.json \\
        --problem-instance problem_instance.h2_o_0.<uuid>.json \\
        --name "..." --email "..." --institution "..." -o solution.json

Schemas are fetched from the QB-GSEE repository and cached under ~/.cache/qbgsee. The
schema URL and version are recorded in every file this writes, so a solution says which
contract it was built against.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

SCHEMA_BASE = ("https://raw.githubusercontent.com/isi-usc-edu/qb-gsee-benchmark/"
               "main/schemas/")
SOLUTION_SCHEMA = "solution.schema.0.0.1.json"
PROBLEM_SCHEMA = "problem_instance.schema.0.0.1.json"
CACHE = Path(os.environ.get("QBGSEE_CACHE", Path.home() / ".cache" / "qbgsee"))

# QB-GSEE requires chemical accuracy; QEncode certifies at a deliberately looser bar so
# that a well-executed run can be certified without also being chemically useful.
QB_ACCURACY_HA = 0.00159362
QENCODE_CERT_HA = 0.010

# QB-GSEE short_name -> QEncode molecule. Only exact chemical matches; QEncode's H4, H6,
# H8, H10, C4H4, C4H6, benzene, water dimer and BeH2 have no QB-GSEE counterpart, and
# QB-GSEE's atoms, halogens and transition metals have none in QEncode.
MOLECULE_MAP = {
    "h2_o_0": "H2O",
    "h_f_0": "HF",
    "li_h_0": "LiH",
    "n2_0": "N2",
    "n_h3_0": "NH3",
}

# A stable identity for QEncode as a solver, so successive submissions are attributable to
# the same solver rather than to a fresh random UUID each time.
SOLVER_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL,
                             "https://www.qencode-benchmark.org/solver/vqe"))


def _schema(name: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / name
    if not p.exists():
        url = SCHEMA_BASE + name
        with urllib.request.urlopen(url, timeout=60) as r:      # nosec - fixed host
            p.write_bytes(r.read())
    return json.loads(p.read_text())


def _entries(repo: Path):
    for f in sorted((repo / "releases" / "v4" / "db").glob("*.json")):
        try:
            yield f, json.loads(f.read_text())
        except Exception:
            continue


def cmd_compare(args):
    repo = Path(os.environ.get("QENCODE_REPO", os.getcwd()))
    best = {}
    for f, d in _entries(repo):
        mol = f.name.split("_")[0]
        g = (d.get("results", {}).get("quality", {}) or {}).get("abs_vqe_exact_gap")
        if g is None:
            continue
        if mol not in best or g < best[mol][0]:
            best[mol] = (g, d)

    print("QB-GSEE accuracy requirement : %.8f Ha  (%.2f mHa, chemical accuracy)"
          % (QB_ACCURACY_HA, QB_ACCURACY_HA * 1000))
    print("QEncode certification bar    : %.8f Ha  (%.2f mHa, %.1fx looser)"
          % (QENCODE_CERT_HA, QENCODE_CERT_HA * 1000, QENCODE_CERT_HA / QB_ACCURACY_HA))
    print()
    print("%-10s %-10s %-32s %12s %9s %9s"
          % ("QB-GSEE", "QEncode", "best QEncode entry", "gap (Ha)", "QEncode", "QB-GSEE"))
    print("-" * 92)
    n = passed = 0
    for qb, mol in sorted(MOLECULE_MAP.items()):
        if mol not in best:
            print("%-10s %-10s %-32s %12s %9s %9s" % (qb, mol, "(no entry)", "-", "-", "-"))
            continue
        g, d = best[mol]
        n += 1
        ok = g < QB_ACCURACY_HA
        passed += ok
        print("%-10s %-10s %-32s %12.3e %9s %9s"
              % (qb, mol, d["entry_id"].split("__")[0][:32], g,
                 "pass" if g < QENCODE_CERT_HA else "FAIL",
                 "pass" if ok else "FAIL"))
    print("-" * 92)
    print("  %d of %d overlapping molecules meet the QB-GSEE accuracy requirement." % (passed, n))
    print()
    print("  Caveat that matters: QB-GSEE instances carry their own FCIDUMP integrals and")
    print("  active spaces. A QEncode gap is measured against ITS OWN active-space CASCI")
    print("  reference, so this compares accuracy achieved on comparable problems, not on")
    print("  byte-identical ones. Running the actual QB-GSEE FCIDUMPs is a separate job and")
    print("  needs their SFTP data access.")


def _iso(ts=None):
    return (ts or _dt.datetime.now(_dt.timezone.utc)).isoformat().replace("+00:00", "Z")


def cmd_export(args):
    entry = json.loads(Path(args.entry).read_text())
    pi = None
    if args.problem_instance:
        pi = json.loads(Path(args.problem_instance).read_text())

    res = entry.get("results", {})
    q = res.get("quality", {}) or {}
    vqe = res.get("vqe", {}) or {}
    cs = entry.get("circuit_stats", {}) or {}
    prov = entry.get("provenance", {}) or {}

    energy = vqe.get("best_energy_hartree")
    gap = q.get("abs_vqe_exact_gap")

    if pi is not None:
        pi_uuid = pi["problem_instance_uuid"]
        tasks = pi.get("tasks") or []
        basis = ((entry.get("problem") or {}).get("basis") or "").lower().replace("-", "")
        matches = [t for t in tasks
                   if basis and basis in str((t.get("features") or {})
                                             .get("molecule_name", "")).lower().replace("-", "")]
        if args.task_uuid:
            task_uuid = args.task_uuid
        elif len(tasks) == 1:
            task_uuid = tasks[0]["task_uuid"]
        elif len(matches) == 1:
            # An instance carries one task per basis set. Submitting a cc-pVDZ result
            # against the cc-pVQZ task would be a silent category error, so match on it.
            task_uuid = matches[0]["task_uuid"]
            print("  matched task by basis %s: %s"
                  % ((entry.get("problem") or {}).get("basis"), task_uuid), file=sys.stderr)
        else:
            raise SystemExit(
                "problem instance has %d tasks and %d matched this entry's basis; "
                "pass --task-uuid:\n  %s"
                % (len(tasks), len(matches),
                   "\n  ".join("%s  %s" % (t["task_uuid"],
                                           (t.get("features") or {}).get("molecule_name", ""))
                               for t in tasks)))
    else:
        if not (args.problem_instance_uuid and args.task_uuid):
            raise SystemExit("give --problem-instance FILE, or both "
                             "--problem-instance-uuid and --task-uuid")
        pi_uuid, task_uuid = args.problem_instance_uuid, args.task_uuid

    # Deterministic solution UUID: the same entry against the same task always produces
    # the same identifier, so re-exporting does not manufacture a new submission.
    sol_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL,
                              "qencode|%s|%s" % (entry.get("entry_id"), task_uuid)))

    # quantum_resources.logical requires num_logical_qubits, num_T_gates_per_shot and
    # num_shots. QEncode records the first two (or an honest substitute) and has no notion
    # of shots at all, since its energies come from exact statevector simulation.
    logical = {}
    if cs.get("t_gate_estimate") is not None:
        logical["num_T_gates_per_shot"] = int(cs["t_gate_estimate"])
    if cs.get("toffoli_gate_estimate") is not None:
        logical["num_toffoli_gates_per_shot"] = int(cs["toffoli_gate_estimate"])
    if cs.get("logical_qubits") is not None:
        logical["num_logical_qubits"] = int(cs["logical_qubits"])
    elif cs.get("num_qubits_tapered") is not None:
        # Fall back to the simulated register. Flagged in solution_details so a reader is
        # not left thinking this is a fault-tolerant logical count.
        logical["num_logical_qubits"] = int(cs["num_qubits_tapered"])
    # The T-gate figure is a single-run qubitized-QPE estimate at the recorded synthesis
    # precision, so one shot is the matching count. The reported ENERGY did not come from
    # sampling at all; solution_details says so rather than leaving it implied.
    logical["num_shots"] = 1

    # QB-GSEE requires run_time.overall_time.seconds. QEncode entries record nfev but no
    # wall-clock time, so there is nothing honest to put here unless the caller supplies
    # one. Writing 0.0 would read as "instantaneous", so this refuses instead.
    if args.run_time_seconds is None:
        raise SystemExit(
            "QB-GSEE requires run_time.overall_time.seconds, and QEncode entries do not\n"
            "record wall-clock time (this entry records nfev = %s and nothing else).\n"
            "Pass --run-time-seconds <measured value>, or --run-time-seconds 0 to declare\n"
            "it unmeasured. This tool will not invent a runtime." % vqe.get("nfev"))
    run_time = {"overall_time": {"seconds": float(args.run_time_seconds)}}

    sol = {
        "$schema": SCHEMA_BASE + SOLUTION_SCHEMA,
        "solution_uuid": sol_uuid,
        "problem_instance_uuid": pi_uuid,
        "creation_timestamp": _iso(),
        "contact_info": [{"name": args.name, "email": args.email,
                          "institution": args.institution}],
        # QEncode's energies come from exact statevector simulation and its quantum
        # resources from a qubitized-QPE model, so nothing here was executed on hardware.
        "is_resource_estimate": True,
        "solution_data": [{
            "task_uuid": task_uuid,
            "energy": float(energy) if energy is not None else None,
            "energy_units": "Hartree",
            "error_bound": float(gap) if gap is not None else None,
            "confidence_level": 1.0 if gap is not None else None,
            "quantum_resources": {"logical": logical} if logical else {"logical": {}},
            "run_time": run_time,
            "solution_details": {
                "qencode_entry_id": entry.get("entry_id"),
                "qencode_entry_hash_sha256": prov.get("entry_hash_sha256"),
                "ansatz": (entry.get("encoding") or {}).get("ansatz_type"),
                "ansatz_reps": (entry.get("encoding") or {}).get("ansatz_reps"),
                "mapping": (entry.get("encoding") or {}).get("mapping"),
                "active_space": ((entry.get("problem") or {}).get("active_space")),
                "optimizer": (entry.get("run_config") or {}).get("optimizer"),
                "backend": (entry.get("run_config") or {}).get("backend_type"),
                "basis": (entry.get("problem") or {}).get("basis"),
                "reference": q.get("gap_reference"),
                "error_bound_definition":
                    "absolute difference between the VQE energy and exact diagonalisation "
                    "of the same qubit Hamiltonian in the same active space",
                "logical_qubit_source":
                    "fault-tolerant estimate" if cs.get("logical_qubits") is not None
                    else "simulated register size after tapering, not a fault-tolerant count",
                "noiseless": True,
                "energy_source":
                    "exact statevector simulation; no sampling, so num_shots is not "
                    "meaningful for the reported energy and is set to 1 to match the "
                    "single-run qubitized-QPE resource estimate",
                "t_gate_synthesis_epsilon": cs.get("t_gate_synthesis_epsilon"),
                "leaderboard": "https://www.qencode-benchmark.org/entry/%s"
                               % entry.get("entry_id"),
            },
        }],
        "solver_details": {
            "solver_uuid": SOLVER_UUID,
            "solver_short_name": "QEncode-VQE",
            "compute_hardware_type": "classical_simulator",
            "software": {
                "name": "QEncode",
                "url": "https://github.com/qencode-benchmark/qencode-benchmark",
                "tool_versions": prov.get("tool_versions"),
            },
        },
        # QEncode signs entries with Ed25519, but over its own payload rather than over the
        # QB-GSEE object, so presenting it here would misrepresent what was signed. The
        # entry hash is carried in solution_details instead, which is verifiable.
        "digital_signature": None,
    }

    out = json.dumps(sol, indent=1, sort_keys=False)
    if args.output:
        Path(args.output).write_text(out + "\n")
        print("wrote %s" % args.output)
    else:
        print(out)

    if not args.no_validate:
        _validate(sol)


def _validate(sol):
    try:
        import jsonschema
    except ImportError:
        print("\n  jsonschema not installed; skipping validation "
              "(pip install jsonschema)", file=sys.stderr)
        return
    schema = _schema(SOLUTION_SCHEMA)
    # The schema references sibling files by relative name.
    store = {}
    for dep in ("uuid.schema.json", "timestamp.schema.json"):
        try:
            store[dep] = _schema(dep)
        except Exception:
            pass
    try:
        resolver = jsonschema.RefResolver(base_uri="", referrer=schema, store=store)
        jsonschema.validate(sol, schema, resolver=resolver)
        print("\n  VALID against %s" % SOLUTION_SCHEMA, file=sys.stderr)
    except jsonschema.ValidationError as e:
        print("\n  INVALID: %s" % str(e).split("\n")[0], file=sys.stderr)
        print("  at: %s" % "/".join(str(x) for x in e.absolute_path), file=sys.stderr)
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="molecule overlap and accuracy against QB-GSEE")
    c.set_defaults(func=cmd_compare)

    e = sub.add_parser("export", help="render a QEncode entry as a QB-GSEE solution")
    e.add_argument("entry")
    e.add_argument("--problem-instance", help="a QB-GSEE problem_instance.json")
    e.add_argument("--problem-instance-uuid")
    e.add_argument("--task-uuid")
    e.add_argument("--name", required=True)
    e.add_argument("--email", required=True)
    e.add_argument("--institution", required=True)
    e.add_argument("-o", "--output")
    e.add_argument("--run-time-seconds", type=float,
                   help="measured wall-clock seconds. Required, because QEncode entries "
                        "do not record it and this tool will not invent one.")
    e.add_argument("--no-validate", action="store_true")
    e.set_defaults(func=cmd_export)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
