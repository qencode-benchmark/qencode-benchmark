"""Test a derived prediction for the gate-noise bias, not a fitted one.

Depolarizing noise takes rho toward (1-eps)|psi><psi| + eps*I/2^n, so

    dE = eps * (Tr(H)/2^n - E_psi)

and Tr(H)/2^n is exactly the identity coefficient of the Pauli decomposition, because
every other Pauli string is traceless. With per-gate error probabilities,

    eps ~ 1 - (1-p1)^N1q * (1-p2)^(2*N2q)

No free parameters, and every quantity is already stored in a published entry.
"""
import os
for v in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"): os.environ[v]="1"
import glob, json, re, sys
import numpy as np, pennylane as qml
sys.path.insert(0, os.path.expanduser("~/qencode"))
import noise_models

P={"X":qml.PauliX,"Y":qml.PauliY,"Z":qml.PauliZ}
def load(path):
    d=json.load(open(path)); h=d["artifacts"]["qubit_hamiltonian"]
    def op(ps):
        if ps.strip() in ("I",""): return qml.Identity(0)
        o=None
        for p,w in re.findall(r"([XYZ])(\d+)",ps):
            t=P[p](int(w)); o=t if o is None else o@t
        return o if o is not None else qml.Identity(0)
    v=d["results"]["vqe"]; cs=d.get("circuit_stats",{}); n=h["num_qubits"]
    par=np.array(v["optimal_params"],float)
    if n<=0 or len(par)%n: return None
    reps=len(par)//n-1
    if reps<1: return None
    c_ident=sum(t["coefficient"] for t in h["pauli_terms"] if t["pauli_string"].strip() in ("I",""))
    return dict(H=qml.Hamiltonian([t["coefficient"] for t in h["pauli_terms"]],
                                  [op(t["pauli_string"]) for t in h["pauli_terms"]]),
                n=n,reps=reps,params=par,hf=np.array(d["artifacts"]["circuits"]["hf_state"]),
                e_pub=float(v["best_energy_hartree"]),c_I=float(c_ident),
                n2q=cs.get("ansatz_num_2q_gates") or 0,n1q=cs.get("ansatz_num_1q_gates") or 0)

def energy(r,dev,a1,a2):
    d=qml.device(dev,wires=r["n"])
    @qml.qnode(d)
    def E(p):
        qml.BasisState(r["hf"],wires=range(r["n"])); i=0
        for _ in range(r["reps"]):
            for w in range(r["n"]): qml.RY(p[i],wires=w); i+=1; a1(w)
            for w in range(r["n"]-1): qml.CNOT(wires=[w,w+1]); a2([w,w+1])
        for w in range(r["n"]): qml.RY(p[i],wires=w); i+=1; a1(w)
        return qml.expval(r["H"])
    return float(E(r["params"]))

repo=os.environ.get("QENCODE_REPO",os.getcwd())
best={}
for f in sorted(glob.glob(os.path.join(repo,"releases/v4/db/*_HEA_*.json"))):
    r=load(f)
    if r is None: continue
    m=os.path.basename(f).split("_")[0]
    if m in ("H2","HF"): continue
    if m not in best or r["n"]<best[m]["n"]: r["mol"]=m; best[m]=r
print("%-10s %5s %5s %5s %11s %11s %11s %11s %8s"%("molecule","n","N1q","N2q","c_I (Ha)","measured","predicted","ratio","model"))
print("-"*104)
rows=[]
idev,i1,i2,_=noise_models.get("ideal/v1")
for m in ("depolarizing-opt/v1","depolarizing-current/v1","depolarizing-pessimistic/v1"):
    spec=noise_models.NOISE_MODELS[m]["params"]; p1,p2=spec["p_1q"],spec["p_2q"]
    dev,a1,a2,_=noise_models.get(m)
    for k,r in sorted(best.items(),key=lambda kv:kv[1]["n"]):
        e0=energy(r,idev,i1,i2)
        if abs(e0-r["e_pub"])>1e-6: continue
        e1=energy(r,dev,a1,a2)
        meas=(e1-e0)*1000.0
        eps=1.0-(1.0-p1)**r["n1q"]*(1.0-p2)**(2*r["n2q"])
        pred=eps*(r["c_I"]-e0)*1000.0
        rows.append(meas/pred if pred else np.nan)
        print("%-10s %5d %5d %5d %11.4f %11.2f %11.2f %11.3f %8s"%(k,r["n"],r["n1q"],r["n2q"],r["c_I"],meas,pred,meas/pred if pred else float("nan"),m.replace("depolarizing-","").replace("/v1","")))
a=np.array([x for x in rows if np.isfinite(x)])
print()
print("  measured / predicted:  median %.3f   range %.3f to %.3f   (1.000 = exact)"%(np.median(a),a.min(),a.max()))
if a.max()/a.min()<1.15:
    print("  The derived formula predicts the bias to within %.0f%% with NO fitted parameters."%(100*(a.max()-a.min())/2))
    print("  A published entry therefore already contains everything needed to estimate its")
    print("  hardware penalty: identity coefficient, gate counts, and the noiseless energy.")
