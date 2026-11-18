#!/usr/bin/env python3
"""Check that every 3D model a footprint library names exists in this library.

Reads every ``.kicad_mod`` file under a footprint library checkout (for Trace,
https://github.com/buildwithtrace/trace-kicad-footprints-lib), takes each
``(model "...")`` path, maps ``${KICAD<n>_3DMODEL_DIR}/<lib>.3dshapes/<name>.step``
to ``<lib>.3dshapes/<name>.step`` in this repository, and reports every path
that does not exist here.

The comparison is case-sensitive on every OS (it compares against the real
directory listing), so a name that only matches on a case-insensitive disk
is still reported.

Exit status: 0 when every model resolves (or is listed in --allowlist),
1 when any does not, 2 on a usage error.

Python 3.8+, standard library only.

Examples:
    python3 tools/check_footprint_models.py ../trace-kicad-footprints-lib
    git ls-tree -r --name-only HEAD > /tmp/models.txt
    python3 tools/check_footprint_models.py ../trace-kicad-footprints-lib \\
        --models-list /tmp/models.txt
    python3 tools/check_footprint_models.py ../trace-kicad-footprints-lib \\
        --allowlist tools/known_missing_models.txt --write-missing missing.txt
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

# (model "path" ...) or (model path ...); KiCad escapes \" and \\ inside quotes.
MODEL_RE = re.compile(r'\(model\s+("(?:[^"\\]|\\.)*"|[^\s()"]+)')
# ${KICAD10_3DMODEL_DIR}/..., ${KICAD9_3DMODEL_DIR}/..., ${KICAD_3DMODEL_DIR}/...
# and the old $(VAR) spelling.
VAR_RE = re.compile(r'^(?:\$\{|\$\()(KICAD\d*_3DMODEL_DIR)(?:\}|\))[/\\](.+)$')


def unquote(token):
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return re.sub(r'\\(.)', r'\1', token[1:-1])
    return token


def iter_footprints(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        for name in sorted(filenames):
            if name.endswith('.kicad_mod'):
                yield os.path.join(dirpath, name)


def list_model_files(models_dir):
    """Every file under models_dir as a '/'-separated relative path."""
    found = set()
    for dirpath, dirnames, filenames in os.walk(models_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        rel_dir = os.path.relpath(dirpath, models_dir)
        for name in filenames:
            rel = name if rel_dir == '.' else os.path.join(rel_dir, name)
            found.add(rel.replace(os.sep, '/'))
    return found


def load_allowlist(path):
    entries = set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            if line:
                entries.add(line)
    return entries


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(
        description='Report footprint 3D model paths that do not resolve in this library.')
    ap.add_argument('footprints_dir',
                    help='path to a footprint library checkout (folders of *.pretty/*.kicad_mod)')
    ap.add_argument('--models-dir', default=os.path.dirname(here),
                    help='path to this 3D model library (default: the repo this script is in)')
    ap.add_argument('--models-list', metavar='FILE',
                    help='read the library\'s file paths from FILE (one relative path per line, '
                         'e.g. from `git ls-tree -r --name-only HEAD`) instead of walking '
                         '--models-dir; lets CI check without downloading the models')
    ap.add_argument('--allowlist', metavar='FILE',
                    help='file of <lib>.3dshapes/<name>.step paths known to be missing '
                         '(one per line, # comments); these are reported but do not fail')
    ap.add_argument('--write-missing', metavar='FILE',
                    help='write every unresolved model path (sorted, unique) to FILE')
    ap.add_argument('--max-list', type=int, default=200,
                    help='print at most this many failing lines (default 200; 0 = all)')
    args = ap.parse_args(argv)

    if not os.path.isdir(args.footprints_dir):
        ap.error('not a directory: %s' % args.footprints_dir)
    if args.models_list:
        with open(args.models_list, encoding='utf-8') as fh:
            present = {line.strip().replace(os.sep, '/') for line in fh if line.strip()}
    elif os.path.isdir(args.models_dir):
        present = list_model_files(args.models_dir)
    else:
        ap.error('not a directory: %s' % args.models_dir)
    present_dirs = {p.split('/', 1)[0] for p in present if '/' in p}
    allow = load_allowlist(args.allowlist) if args.allowlist else set()

    n_fp = n_fp_with_model = n_lines = 0
    resolved = 0
    unresolved = defaultdict(list)   # model rel path -> [footprint rel path]
    bad_form = []                    # (footprint, raw path)

    for fp in iter_footprints(args.footprints_dir):
        n_fp += 1
        with open(fp, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
        rel_fp = os.path.relpath(fp, args.footprints_dir).replace(os.sep, '/')
        models = [unquote(m) for m in MODEL_RE.findall(text)]
        if models:
            n_fp_with_model += 1
        for raw in models:
            n_lines += 1
            m = VAR_RE.match(raw)
            if not m:
                bad_form.append((rel_fp, raw))
                continue
            # KiCad normalises the joined path, so "DIR//lib.3dshapes/x.step" still loads.
            rel = re.sub(r'/+', '/', m.group(2).replace('\\', '/')).lstrip('/')
            if '..' in rel.split('/'):
                bad_form.append((rel_fp, raw))
                continue
            if rel in present:
                resolved += 1
            else:
                unresolved[rel].append(rel_fp)

    failing = sorted(p for p in unresolved if p not in allow)
    allowed = sorted(p for p in unresolved if p in allow)
    stale = sorted(allow - set(unresolved))
    folder_absent = Counter(p.split('/', 1)[0] for p in failing
                            if p.split('/', 1)[0] not in present_dirs)

    n_unres_lines = sum(len(v) for v in unresolved.values())
    print('footprints: %d   with a model line: %d   model lines: %d'
          % (n_fp, n_fp_with_model, n_lines))
    print('model lines resolved: %d   unresolved: %d (%d unique paths)'
          % (resolved, n_unres_lines, len(unresolved)))
    print('unique unresolved paths: %d failing, %d allowlisted' % (len(failing), len(allowed)))
    if folder_absent:
        print('failing paths whose whole .3dshapes folder is absent: %d (%d folders)'
              % (sum(folder_absent.values()), len(folder_absent)))
    if bad_form:
        print('model lines not of the form ${KICAD<n>_3DMODEL_DIR}/<path>: %d' % len(bad_form))
    if stale:
        print('allowlist entries that now resolve or are no longer named (remove them): %d'
              % len(stale))
        for p in stale[: args.max_list or None]:
            print('  stale: %s' % p)

    if args.write_missing:
        with open(args.write_missing, 'w', encoding='utf-8') as fh:
            for p in sorted(unresolved):
                fh.write(p + '\n')

    limit = args.max_list or None
    shown = 0
    for p in failing:
        if limit is not None and shown >= limit:
            break
        print('MISSING %s  (named by %s)' % (p, ', '.join(sorted(unresolved[p]))))
        shown += 1
    for fp, raw in bad_form:
        if limit is not None and shown >= limit:
            break
        print('UNRESOLVABLE %s  (in %s)' % (raw, fp))
        shown += 1
    if limit is not None and len(failing) + len(bad_form) > shown:
        print('... %d more not shown (use --max-list 0 or --write-missing FILE)'
              % (len(failing) + len(bad_form) - shown))

    if failing or bad_form:
        print('FAIL: %d model path(s) do not resolve' % (len(failing) + len(bad_form)))
        return 1
    if allowed:
        print('OK: no unresolved model outside the allowlist (%d known-missing allowlisted)'
              % len(allowed))
    else:
        print('OK: every footprint model resolves')
    return 0


if __name__ == '__main__':
    sys.exit(main())
