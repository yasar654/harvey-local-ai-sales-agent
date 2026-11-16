import platform, psutil

def report():
    mem = psutil.virtual_memory().total / (1024**3)
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=2)
        gpu = out.stdout.strip().splitlines() if out.returncode == 0 else []
    except (OSError, subprocess.SubprocessError):
        gpu = []
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        gpu.append("Apple Silicon GPU / shared unified memory (Metal supported by Ollama)")
    if mem >= 48:
        rec = "qwen3:32b (check available memory before loading)"
    elif mem >= 24:
        rec = "qwen3:14b"
    elif mem >= 12:
        rec = "qwen3:8b"
    else:
        rec = "qwen3:4b or a smaller quantized model"
    return {"platform": platform.platform(), "cpu_cores": psutil.cpu_count(logical=True),
            "ram_gb": round(mem, 1), "gpus": gpu, "recommended_model": rec,
            "note": "Recommendation is heuristic; actual performance depends on quantization and available memory."}
