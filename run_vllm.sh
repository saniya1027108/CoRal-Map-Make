# #!/bin/bash

# # Point to the shared Hugging Face cache
# export HF_HOME="/mnt/shared/shared_hf_home"
# export TRANSFORMERS_CACHE="/mnt/shared/shared_hf_home"
# export HF_DATASETS_CACHE="/mnt/shared/shared_hf_home"

# # Use these 4 GPUs
# export CUDA_VISIBLE_DEVICES=4,5,6,7

# vllm serve meta-llama/Llama-3.3-70b-Instruct \
#   --max-model-len 32768 \
#   --gpu-memory-utilization 0.35 \
#   --max-num-seqs 64 \
#   --port 8001 \
#   --tensor-parallel-size 4

#!/bin/bash
set -euo pipefail

# Point to your local Hugging Face cache (writable location)
export HF_HOME="/mnt/data1/nahuja11/.cache/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export HF_DATASETS_CACHE="$HF_HOME"

# Select the 4 GPUs you want vLLM to use
export CUDA_VISIBLE_DEVICES=5
# Optional: tune these values to your hardware and model (see notes below)
# MODEL="meta-llama/Llama-3.1-8B"
PORT=8001

vllm serve Qwen/Qwen3-8B \
  --max-model-len 32k \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 64 \
  --tensor-parallel-size 1 \
  --port "${PORT}" \
  --dtype auto

# # Get the directory where this script is located
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# CHAT_TEMPLATE="${SCRIPT_DIR}/llama3.1_chat_template.jinja"

# vllm serve meta-llama/Llama-3.1-8B \
#   --max-model-len 32k \
#   --gpu-memory-utilization 0.80 \
#   --max-num-seqs 64 \
#   --tensor-parallel-size 1 \
#   --port "${PORT}" \
#   --dtype auto \
#   --trust-remote-code \
#   --chat-template "${CHAT_TEMPLATE}"