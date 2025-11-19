#!/usr/bin/env python3
"""
Scan a directory of .lcp ZIP files, parse JSON files inside each .lcp,
find every object where "activation" == "Reaction", and export a CSV with columns:
  LCP, json_inside_zip, activation_path, Parent_ID, Name, Trigger, Detail

- Parent_ID: nearest ancestor dict's "id" (searches upward)
- Name, Trigger, Detail: keys at the same dict level as "activation" (if present)
"""

import json
import zipfile
import csv
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple

def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")

def find_activation_matches_with_parent(obj: Any) -> List[Dict[str, Optional[str]]]:
    """
    Walk `obj` and return list of matches. Each match dict contains:
      - activation_path: JSON-Pointer-like path to the matched object
      - parent_path: path to the ancestor that provided parent_id (if any)
      - parent_id: the value of nearest ancestor's "id", or None
      - name: value of "name" at the activation object, or None
      - trigger: value of "trigger" at the activation object, or None
      - detail: value of "detail" at the activation object, or None
    """
    results: List[Dict[str, Optional[str]]] = []

    def _recurse(current: Any, path: str, ancestors: List[Any], ancestor_paths: List[str]):
        if isinstance(current, dict):
            if current.get("activation") == "Reaction":
                # find nearest ancestor dict that has an "id"
                parent_id = None
                parent_path = None
                for anc, anc_path in zip(reversed(ancestors), reversed(ancestor_paths)):
                    if isinstance(anc, dict) and "id" in anc:
                        parent_id = anc.get("id")
                        parent_path = anc_path or "/"
                        break
                results.append({
                    "activation_path": path or "/",
                    "parent_path": parent_path,
                    "parent_id": str(parent_id) if parent_id is not None else None,
                    "name": str(current.get("name")) if current.get("name") is not None else None,
                    "trigger": str(current.get("trigger")) if current.get("trigger") is not None else None,
                    "frequency": str(current.get("frequency")) if current.get("frequency") is not None else None,
                    "detail": str(current.get("detail")) if current.get("detail") is not None else None
                })
            # recurse into children
            for k, v in current.items():
                token = _escape(str(k))
                child_path = (path + "/" + token) if path else "/" + token
                _recurse(v, child_path, ancestors + [current], ancestor_paths + [path or "/"])
        elif isinstance(current, (list, tuple)):
            for idx, item in enumerate(current):
                child_path = (path + "/" + str(idx)) if path else "/" + str(idx)
                # push the list itself as an ancestor so the dict above the list is still available
                _recurse(item, child_path, ancestors + [current], ancestor_paths + [path or "/"])
        # primitives: nothing to do

    _recurse(obj, "", [], [])
    return results

def scan_lcp_file_for_matches(lcp_path: Path) -> List[Tuple[str, str, Dict[str, Optional[str]]]]:
    """
    Open .lcp (zip), examine each JSON file, and return list of tuples:
      (str(lcp_path), json_filename_in_zip, match_dict)
    """
    matches: List[Tuple[str, str, Dict[str, Optional[str]]]] = []
    try:
        with zipfile.ZipFile(lcp_path, "r") as z:
            for member in z.namelist():
                if member.endswith("/") or not member.lower().endswith(".json"):
                    continue
                try:
                    raw = z.read(member)
                except KeyError:
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("utf-8", errors="replace")
                try:
                    data = json.loads(text)
                except Exception:
                    # skip unparsable JSON files
                    continue
                for match in find_activation_matches_with_parent(data):
                    matches.append((str(lcp_path), member, match))
    except zipfile.BadZipFile:
        # not a valid zip file; skip
        pass
    return matches

def scan_directory_and_write_csv(dirpath: Path, out_csv: Path):
    dirpath = dirpath.expanduser().resolve()
    out_csv = out_csv.expanduser().resolve()

    fieldnames = ["LCP", "json_inside_zip", "activation_path", "Parent_ID", "Name", "Trigger","Frequency", "Detail"]
    rows: List[Dict[str, Optional[str]]] = []

    for p in sorted(dirpath.iterdir()):
        if p.is_file() and p.suffix.lower() == ".lcp":
            file_matches = scan_lcp_file_for_matches(p)
            for lcp, member, match in file_matches:
                rows.append({
                    "LCP": lcp,
                    "json_inside_zip": member,
                    "activation_path": match.get("activation_path"),
                    "Parent_ID": match.get("parent_id"),
                    "Name": match.get("name"),
                    "Trigger": match.get("trigger"),
                    "Frequency": match.get("frequency"),
                    "Detail": match.get("detail")
                })

    # write CSV
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} matches to {out_csv}")

# Simple CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scan .lcp files for activation=Reaction and export CSV")
    parser.add_argument("dir", help="Directory containing .lcp files")
    parser.add_argument("-o", "--out", default="activation_reaction_report.csv", help="Output CSV path")
    args = parser.parse_args()

    scan_directory_and_write_csv(Path(args.dir), Path(args.out))
