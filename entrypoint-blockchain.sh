#!/bin/bash

# Start Besu
besu --data-path=/app/data \
     --genesis-file=/app/config/genesis.json \
     --node-private-key-file=/app/data/nodekey \
     --rpc-http-enabled \
     --rpc-http-host=0.0.0.0 \
     --rpc-http-api=ETH,NET,CLIQUE,WEB3 \
     --rpc-http-port=${RPC_HTTP_PORT} \
     --p2p-host=0.0.0.0 \
     --host-allowlist=* \
     --sync-min-peers=2