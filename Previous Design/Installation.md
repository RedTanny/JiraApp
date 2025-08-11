conda create -n llama_mcp_jira
conda activate llama_mcp_jira
pip install llama-stack
pip install llama-stack-client
pip install jira

llama stack build --list-templates

#download ollama
curl -fsSL https://ollama.com/install.sh | sh

llama stack build --template ollama --image-type conda

Build spec configuration saved at /home/stanny/.conda/envs/llama_mcp_jira/llamastack-build.yaml
Build Successful!
You can find the newly-built template here: /home/stanny/.local/lib/python3.13/site-packages/llama_stack/templates/ollama/run.yaml
You can run the new Llama Stack distro via: llama stack run /home/stanny/.local/lib/python3.13/site-packages/llama_stack/templates/ollama/run.yaml --image-type conda


export INFERENCE_MODEL=llama3.2:3b


Checking the Server
To verify the server, use:

llama-stack-client models list listing models
llama-stack-client providers list listing providers

