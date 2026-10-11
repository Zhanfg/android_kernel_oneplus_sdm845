#!/usr/bin/env python3
"""Validate exact pinned BakaSU patch anchors and fail-closed behavior."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location('manager_patch', Path(__file__).with_name('patch-bakasu-manager-discovery.py'))
p = module_from_spec(spec)
spec.loader.exec_module(p)
source = p.INCLUDE_ANCHOR + '#include "runtime/ksud.h"\n' + 'void on_boot_completed(void) {\n' + p.ANCHOR + '\n}\n'
patched = p.patch(source)
assert patched != source
assert '#include "manager/manager_identity.h"' in patched
assert 'if (!ksu_has_manager())' in patched
assert 'track_throne(TRACK_THRONE_FORCE_SYNCHRONOUS)' in patched
assert 'track_throne(TRACK_THRONE_PRUNE_ONLY)' in patched
assert patched == p.patch(patched)
for bad in ['no', source.replace('on_boot_completed!', 'new-event')]:
    try:
        p.patch(bad)
        raise AssertionError('Unexpected acceptance of unknown upstream input')
    except ValueError:
        pass
print('PASS: idempotent, signature check preserved, fail closed on unrecognized source')