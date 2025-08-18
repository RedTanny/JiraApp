FROM docker.io/intelanalytics/ipex-llm-inference-cpp-xpu:latest

ENV ZES_ENABLE_SYSMAN=1
ENV OLLAMA_INTEL_GPU=true
ENV OLLAMA_HOST=0.0.0.0:11434

# Define the source and destination directories for symlinks
ENV SOURCE_OLLAMA_DIR="/usr/local/lib/python3.11/dist-packages/bigdl/cpp/libs/ollama"
ENV TARGET_DIR="/llm/ollama"

# Create the target directory and symlink the binaries
RUN mkdir -p ${TARGET_DIR} && \
    ln -sf "${SOURCE_OLLAMA_DIR}/ollama" "${TARGET_DIR}/ollama" && \
    ln -sf "${SOURCE_OLLAMA_DIR}/ollama-lib" "${TARGET_DIR}/ollama-lib" && \
    ln -sf "${SOURCE_OLLAMA_DIR}/libggml-sycl.so" "${TARGET_DIR}/libggml-sycl.so"

# Set the working directory
WORKDIR ${TARGET_DIR}

# Specify the absolute path to the executable
ENTRYPOINT ["/llm/ollama/ollama", "serve"]