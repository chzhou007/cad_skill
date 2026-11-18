"""Bind observed producer processes without treating a Windows PID as unique.

Timestamps are the original observation values. No time or process metadata is
manufactured. Legacy records without epochs are usable only with unique PIDs;
ambiguous parent lifetimes remain unproved instead of being guessed.
"""
from collections import Counter, defaultdict
import os


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(record):
    require(type(record.get('pid')) is int and record['pid'] > 0, 'Positive process PID required')
    started = record.get('started_ns')
    require(started is None or type(started) is int and started > 0, 'Invalid original process start epoch')
    return record['pid'], started


def bind_tree(records, root_pid):
    rows = list(records)
    require(bool(rows), 'Process observations required')
    by_key = {}
    by_pid = defaultdict(list)
    for record in rows:
        key = identity(record)
        require(key not in by_key, 'Repeated process epoch identity')
        if key[1] is not None:
            require(type(record.get('finished_ns')) is int and record['finished_ns'] >= key[1], 'Completed process lifetime required')
        by_key[key] = record
        by_pid[key[0]].append(key)
    require(all(len(keys) == 1 or all(k[1] is not None for k in keys) for keys in by_pid.values()),
            'Reused PID requires original start epochs')
    roots = by_pid.get(root_pid, [])
    require(len(roots) == 1, 'Actual root process epoch is ambiguous')
    root = roots[0]
    parents = {}
    for key, record in by_key.items():
        if key == root:
            continue
        candidates = [p for p in by_pid.get(record['parent_pid'], []) if p != key]
        if key[1] is not None:
            candidates = [p for p in candidates if p[1] is None or p[1] <= key[1] <= by_key[p]['finished_ns']]
        require(len(candidates) == 1, 'Unrelated process or ambiguous parent lifetime')
        parents[key] = candidates[0]
    reached = {root}
    while True:
        children = {key for key, parent in parents.items() if parent in reached}
        if children <= reached:
            break
        reached.update(children)
    require(reached == set(by_key), 'Unrelated process observations cannot be pooled')
    return dict(root=root, records=by_key, parents=parents,
                identity_mode='PID_and_observed_start_ns' if all(k[1] is not None for k in by_key) else 'legacy_unique_PID_unknown_epoch_retained',
                reused_PIDs={pid: len(keys) for pid, keys in by_pid.items() if len(keys) > 1})


def bind_access_records(access_records, tree, epoch_resolver=None):
    by_pid = defaultdict(list)
    for key in tree['records']:
        by_pid[key[0]].append(key)
    bound = {}
    for row in access_records:
        if 'started_ns' in row:
            key = identity(row)
        elif epoch_resolver is not None:
            resolved = epoch_resolver(row)
            key = identity(resolved) if resolved is not None else None
        else:
            key = None
        if key is None:
            candidates = by_pid.get(row['pid'], [])
            require(len(candidates) == 1, 'Adapter receipt for a reused PID requires an epoch binding')
            key = candidates[0]
        require(key in tree['records'] and key not in bound, 'Adapter receipt process epoch differs or repeats')
        require(row.get('parent_pid', tree['records'][key]['parent_pid']) == tree['records'][key]['parent_pid'], 'Adapter parent process differs')
        bound[key] = row
    require(set(bound) == set(tree['records']), 'Observed and adapter process epoch sets differ')
    return bound


def verify_launches(tree, access, observations):
    """Match original spawn tokens and successful ordinary launches by epoch.

    Old ordinary launch records contain PID but no timestamp. Repeated use of
    one PID by the same live parent is necessarily sequential; match its
    creation order to the child's observed start order, never to graph IDs.
    """
    require(set(access) == set(observations) == set(tree['records']), 'Complete epoch-bound process records required')
    tokens = {}
    for parent, row in access.items():
        for request in row.get('multiprocessing_spawn_requests', []):
            token = request['spawn_token']
            require(token not in tokens, 'Repeated original multiprocessing spawn token')
            tokens[token] = parent
    accounted, ordinary, multiprocessing = set(), 0, 0
    for key, row in access.items():
        token = row.get('multiprocessing_spawn_token')
        if token:
            require(token in tokens and tokens.pop(token) == tree['parents'].get(key), 'Multiprocessing parent epoch differs')
            accounted.add(key)
            multiprocessing += 1
    require(not tokens, 'Spawned multiprocessing child has no receipt')
    for parent, observation in observations.items():
        launches = defaultdict(list)
        node_launches = Counter()
        for row in observation.get('qualified_subprocesses', []):
            if row['outcome'] != 'created':
                continue
            require(row['parent_pid'] == parent[0], 'Ordinary launch parent PID differs')
            if row['executable_role'] == 'qualified_node':
                node_launches[row['pid']] += 1
            else:
                launches[row['pid']].append(row)
        node_proofs = Counter(r['pid'] for r in access[parent].get('qualified_node_calls', []))
        require(node_launches == node_proofs, 'Qualified Node launches and original bridge proofs differ')
        for pid, rows in launches.items():
            children = sorted((key for key, p in tree['parents'].items() if p == parent and key[0] == pid and key not in accounted),
                              key=lambda key: -1 if key[1] is None else key[1])
            require(len(children) == len(rows), 'Ordinary launch count and child epochs differ')
            for child, launch in zip(children, rows):
                require(child not in accounted, 'Child epoch counted twice')
                accounted.add(child)
                ordinary += 1
    require(accounted == set(tree['records']) - {tree['root']}, 'Python child is not bound to an actual launch or original spawn token')
    return dict(processes=len(tree['records']), ordinary_qualified_Python_children=ordinary,
                multiprocessing_children=multiprocessing, reused_PIDs=tree['reused_PIDs'],
                every_Python_child_launch_and_receipt_accounted=True, identity_mode=tree['identity_mode'])


def windows_process_probe(pid):
    """Read a real handle's creation/exit state; distinguish access errors."""
    require(os.name=='nt','Windows process probe is available on Windows only')
    import ctypes
    class FileTime(ctypes.Structure):
        _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
    kernel.GetProcessTimes.argtypes=[ctypes.c_void_p,*([ctypes.POINTER(FileTime)]*4)]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:
        error=ctypes.get_last_error()
        if error in (87,1168):return None
        raise OSError(error,'Process lifetime could not be verified')
    try:
        creation,exit_time,kernel_time,user_time=FileTime(),FileTime(),FileTime(),FileTime()
        code=ctypes.c_uint32()
        if not kernel.GetProcessTimes(handle,*map(ctypes.byref,(creation,exit_time,kernel_time,user_time)))or not kernel.GetExitCodeProcess(handle,ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        ticks=(creation.high<<32)|creation.low
        return dict(created_ns=(ticks-116444736000000000)*100,terminated=bool(exit_time.high or exit_time.low),exit_code=code.value)
    finally:kernel.CloseHandle(handle)


def same_epoch_live(pid,observed_started_ns,probe=windows_process_probe):
    require(type(observed_started_ns)is int and observed_started_ns>0,'Actual observation epoch required for liveness')
    state=probe(pid)
    if state is None:return False
    require(type(state.get('created_ns'))is int and type(state.get('terminated'))is bool,'Verified process creation and exit state required')
    if state['created_ns']>observed_started_ns:
        return False  # This PID now belongs to a later process instance.
    return not state['terminated']
