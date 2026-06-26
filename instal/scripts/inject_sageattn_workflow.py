#!/usr/bin/env python3
"""
Inject SageAttention-T4 Apply node into ComfyUI workflow JSON.

Inserts SageAttentionT4_Apply between model-producing nodes
(loaders) and model-consuming nodes (samplers).

Usage:
  python inject_sageattn_workflow.py workflow.json [--output fixed.json]
  python inject_sageattn_workflow.py ComfyUI/user/default/workflows/
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, Any, List, Tuple


# Nodes that produce model outputs (loaders).
MODEL_PRODUCERS = {
    "CheckpointLoaderSimple", "LTXVLoader", "FluxLoader",
    "UNETLoader", "DiffusionLoader", "CheckpointLoader",
}

# Nodes that consume model inputs (samplers, guiders).
# SageAttention is only injected BEFORE these.
MODEL_CONSUMERS = {
    "KSampler", "KSamplerAdvanced", "LTXVSampler", "FluxSampler",
    "BasicGuider", "BasicScheduler", "SamplerCustom",
    "LTXVDualCFGGuider", "LTXVGuider",
}


def generate_id(workflow: dict) -> str:
    max_id = 0
    for k in workflow:
        if k.isdigit():
            max_id = max(max_id, int(k))
    return str(max_id + 1)


def find_model_connections(workflow: dict) -> List[Tuple[str, str, int]]:
    connections = []
    for node_id, node_data in workflow.items():
        # Only inject before known consumer nodes (samplers, guiders)
        target_class = node_data.get('class_type', '')
        if MODEL_CONSUMERS and target_class not in MODEL_CONSUMERS:
            continue
        inputs = node_data.get('inputs', {})
        model_input = inputs.get('model')
        if isinstance(model_input, list) and len(model_input) == 2:
            source_id, source_slot = model_input
            if isinstance(source_id, str) and isinstance(source_slot, int):
                src_class = workflow.get(source_id, {}).get('class_type', '')
                # Skip if source is already SageAttention (prevents double-injection)
                if src_class == 'SageAttentionT4_Apply':
                    continue
                connections.append((source_id, node_id, source_slot))
    return connections


def inject_sageattn(workflow: dict):
    connections = find_model_connections(workflow)
    if not connections:
        return workflow, 0

    groups = defaultdict(list)
    for src, tgt, slot in connections:
        groups[src].append((tgt, slot))

    next_id = int(generate_id(workflow))
    injected = 0

    for source_id, consumers in groups.items():
        sage_id = str(next_id)
        next_id += 1
        workflow[sage_id] = {
            'class_type': 'SageAttentionT4_Apply',
            'inputs': {
                'model': [source_id, 0],
                'smooth_k': True,
                'enable': True,
            }
        }
        for target_id, slot in consumers:
            if target_id in workflow:
                workflow[target_id]['inputs']['model'] = [sage_id, 0]
        injected += 1

    return workflow, injected


def inject_file(filepath: str, output_path: str = None) -> int:
    with open(filepath, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    workflow, count = inject_sageattn(workflow)

    if count == 0:
        print(f'  skip {filepath}: no model connections')
        return 0

    out = output_path or filepath
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)

    print(f'  OK {filepath}: injected {count} SageAttention-T4 node(s)')
    return count


def inject_directory(dirpath: str) -> int:
    total = 0
    for fname in sorted(os.listdir(dirpath)):
        if fname.endswith('.json'):
            fpath = os.path.join(dirpath, fname)
            try:
                total += inject_file(fpath)
            except (json.JSONDecodeError, KeyError) as e:
                print(f'  WARN {fpath}: {e}')
    return total


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python inject_sageattn_workflow.py <workflow.json|dir>')
        sys.exit(1)

    target = sys.argv[1]
    output = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    print(f'Injecting SageAttention-T4 into: {target}')

    if os.path.isdir(target):
        total = inject_directory(target)
    else:
        total = inject_file(target, output)

    print(f'Done: {total} SageAttention-T4 node(s) injected')
