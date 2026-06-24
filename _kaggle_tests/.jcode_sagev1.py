import subprocess, os
vp = "/kaggle/working/venv/bin/python"
env = dict(os.environ); env["UV_LINK_MODE"]="copy"
print("=== установка sageattention v1 ===")
r = subprocess.run(["uv","pip","install","--python",vp,"sageattention==1.0.6"],
                   capture_output=True,text=True,env=env)
print((r.stdout+r.stderr)[-600:], "RC:", r.returncode)

bench = r'''
import torch, time
torch.manual_seed(0)
dev="cuda"
B,H,S,D = 1,24,4096,128
q=torch.randn(B,H,S,D,device=dev,dtype=torch.float16)
k=torch.randn(B,H,S,D,device=dev,dtype=torch.float16)
v=torch.randn(B,H,S,D,device=dev,dtype=torch.float16)

def timeit(fn,iters=20):
    fn(); torch.cuda.synchronize()
    t=time.time()
    for _ in range(iters): o=fn()
    torch.cuda.synchronize()
    return (time.time()-t)/iters*1000, o

# baseline SDPA
def sdpa(): return torch.nn.functional.scaled_dot_product_attention(q,k,v)
ms_sdpa,o_sdpa = timeit(sdpa)
print(f"SDPA: {ms_sdpa:.2f} ms/iter")

# SageAttention v1
try:
    from sageattention import sageattn
    def sage(): return sageattn(q,k,v,tensor_layout="HND",is_causal=False)
    out0 = sage()  # первый вызов — компиляция Triton
    torch.cuda.synchronize()
    ms_sage,o_sage = timeit(sage)
    diff = (o_sage.float()-o_sdpa.float()).abs().mean().item()
    print(f"SAGE v1: {ms_sage:.2f} ms/iter | mean|diff| vs SDPA = {diff:.4f}")
    print(f"speedup vs SDPA: x{ms_sdpa/ms_sage:.2f}")
except Exception as e:
    import traceback; traceback.print_exc()
    print("SAGE FAILED:", repr(e))
'''
r2 = subprocess.run([vp,"-c",bench],capture_output=True,text=True,env=env,cwd="/kaggle/working")
print("=== бенчмарк ===")
print(r2.stdout)
print("ERR_TAIL:", r2.stderr[-1500:])
