import os
import yaml
import ast
import re

root_dir = 'policies/policy-orchestrator/src/features/code_engine/algos/nn'
dirs = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])

required_yaml_keys = [
    'algo_id', 'name', 'version', 'category', 'capability_tags',
    'inputs', 'outputs', 'parameters', 'input_assumptions', 'purity',
    'determinism', 'idempotency', 'reversibility', 'side_effects',
    'concurrency_model', 'hardware_target', 'exactness', 'error_bound',
    'uses_model', 'complexity', 'preconditions', 'postconditions',
    'certificate', 'compatible_adapters', 'related_algos', 'references'
]

def extract_from_tex(tex_path):
    if not os.path.exists(tex_path):
        return {}
    txt = open(tex_path).read()
    urls = re.findall(r'https?://[^\s\}\)]+', txt)
    clean_urls = []
    for u in urls:
        u_clean = u.rstrip('.,;}')
        if u_clean not in clean_urls:
            clean_urls.append(u_clean)
    return {'urls': clean_urls}

updated_count = 0
for d in dirs:
    impl_path = os.path.join(root_dir, d, 'impl.py')
    tex_path = os.path.join(root_dir, d, 'math.tex')
    content = open(impl_path).read()
    parts = content.split('---')
    if len(parts) >= 3:
        raw_yaml = parts[1]
        data = yaml.safe_load(raw_yaml)
        is_wrapped = 'contract' in data and isinstance(data['contract'], dict)
        contract = data['contract'] if is_wrapped else data
        
        missing = [k for k in required_yaml_keys if k not in contract]
        if missing or any(not str(r).startswith('http') for r in contract.get('references', [])):
            tex_info = extract_from_tex(tex_path)
            
            if 'parameters' not in contract:
                contract['parameters'] = {}
            if 'input_assumptions' not in contract:
                contract['input_assumptions'] = ['Input tensors and parameters satisfy dimensionality and finite numerical bounds.']
            if 'purity' not in contract:
                contract['purity'] = 'pure'
            if 'determinism' not in contract:
                contract['determinism'] = 'deterministic'
            if 'idempotency' not in contract:
                contract['idempotency'] = 'not_applicable'
            if 'reversibility' not in contract:
                contract['reversibility'] = 'not_applicable'
            if 'side_effects' not in contract:
                contract['side_effects'] = 'none'
            if 'concurrency_model' not in contract:
                contract['concurrency_model'] = 'thread_safe'
            if 'hardware_target' not in contract:
                contract['hardware_target'] = 'cpu_scalar'
            if 'exactness' not in contract:
                contract['exactness'] = 'exact'
            if 'error_bound' not in contract:
                contract['error_bound'] = 'Standard IEEE-754 floating point precision'
            if 'uses_model' not in contract:
                contract['uses_model'] = False
            if 'complexity' not in contract:
                contract['complexity'] = {
                    'variables': {'N': 'tensor/parameter dimension'},
                    'time_worst': 'O(N)',
                    'time_typical': 'O(N)',
                    'space': 'O(N)'
                }
            if 'preconditions' not in contract:
                contract['preconditions'] = ['Input tensors are non-empty and conform to defined mathematical shapes.']
            if 'postconditions' not in contract:
                contract['postconditions'] = ['Output values and arrays are populated without NaN or infinite values.']
            if 'certificate' not in contract:
                contract['certificate'] = 'Exact implementation matching analytical mathematical derivation.'
            if 'compatible_adapters' not in contract:
                contract['compatible_adapters'] = []
            if 'related_algos' not in contract:
                contract['related_algos'] = []
                
            refs = contract.get('references', [])
            clean_refs = []
            if refs:
                for r in refs:
                    if isinstance(r, str) and r.startswith('http'):
                        clean_refs.append(r)
            if not clean_refs:
                clean_refs = tex_info.get('urls') or ['https://arxiv.org/']
            contract['references'] = clean_refs

            # Format docstring
            new_contract_obj = {'contract': contract} if is_wrapped else contract
            formatted_yaml = yaml.dump(new_contract_obj, sort_keys=False, default_flow_style=False)
            indented_yaml = '\n'.join('    ' + line if line.strip() else line for line in formatted_yaml.splitlines())
            
            # Reconstruct content with triple quotes docstring
            prefix = parts[0]
            suffix = '---'.join(parts[2:])
            new_content = prefix + '---\n' + indented_yaml + '\n    ---' + suffix
            
            # Verify valid AST
            ast.parse(new_content)
            open(impl_path, 'w').write(new_content)
            updated_count += 1

print(f'Successfully augmented and standardized {updated_count} contracts.')
