import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Query qencode-db index.json")
    parser.add_argument("--molecule", type=str, default=None, help="Filter by molecule name (e.g., H2)")
    parser.add_argument("--basis", type=str, default=None, help="Filter by basis (e.g., sto3g)")
    parser.add_argument("--mapping", type=str, default=None, help="Filter by mapping (e.g., jordan_wigner)")
    parser.add_argument("--max-qubits", type=int, default=None, help="Filter by max qubits")
    parser.add_argument("--ansatz", type=str, default=None, help="Filter by ansatz type (e.g., uccsd, hardware_efficient)")
    parser.add_argument("--active-space", type=str, default=None, help="Filter by active space: true/false")
    parser.add_argument("--validated", action="store_true", help="Only show entries with HF energy present")
    parser.add_argument("--has-exact-min", action="store_true", help="Only show entries with exact min eigenvalue present")
    parser.add_argument("--sort", type=str, default=None, help="Sort by: qubits, vqe, hf, terms")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    index_path = project_root / "db" / "index.json"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows = index["entries"]

    def parse_bool(s: str):
        s = s.strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
        raise ValueError("Use true/false")

    def match(r):

        if args.ansatz and (r.get("ansatz_type") or "").lower() != args.ansatz.lower():
            return False

        if args.active_space is not None:
            want = parse_bool(args.active_space)
            if bool(r.get("active_space_enabled")) != want:
                return False

        if args.validated:
            if r.get("hf_energy_hartree") is None:
                return False

        if args.has_exact_min:
            if r.get("exact_qubit_min_eig_hartree_like") is None:
                return False

        if args.molecule and (r.get("molecule") or "").lower() != args.molecule.lower():
            return False
        if args.basis and (r.get("basis") or "").lower() != args.basis.lower():
            return False
        if args.mapping and (r.get("mapping") or "").lower() != args.mapping.lower():
            return False
        if args.max_qubits is not None:
            nq = r.get("num_qubits")
            if nq is None or nq > args.max_qubits:
                return False
        return True

    filtered = [r for r in rows if match(r)]
    if args.sort:
        key = args.sort.lower()
        def sort_key(row):
            if key == "qubits":
                return (row.get("num_qubits") is None, row.get("num_qubits", 10**9))
            if key == "terms":
                return (row.get("num_pauli_terms") is None, row.get("num_pauli_terms", 10**9))
            if key == "hf":
                return (row.get("hf_energy_hartree") is None, row.get("hf_energy_hartree", 10**9))
            if key == "vqe":
                return (row.get("vqe_best_energy_hartree") is None, row.get("vqe_best_energy_hartree", 10**9))
            return (False, 0)
        filtered = sorted(filtered, key=sort_key)

    print(f"Found {len(filtered)} / {len(rows)} entries")
    for r in filtered:
        print(
            f"- {r['file']} | mol={r['molecule']} basis={r['basis']} map={r['mapping']} "
            f"ansatz={r.get('ansatz_type')} reps={r.get('ansatz_reps')} storage={r.get('ansatz_storage')} "
            f"AS={r.get('active_space_enabled')} "
            f"qubits={r['num_qubits']} terms={r['num_pauli_terms']} "
            f"HF={r.get('hf_energy_hartree')} VQE={r.get('vqe_best_energy_hartree')} "
            f"vqe_method={r.get('vqe_method')} exact_min={r.get('exact_qubit_min_eig_hartree_like')}"
        )


if __name__ == "__main__":
    main()

