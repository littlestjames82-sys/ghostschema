"""Local $ref graph helpers.

A $ref is local only when it is exactly "#" or starts with "#/".
Everything else (https URLs, file paths, bare fragments into other
documents) is external: GhostSchema never fetches it. External refs
are recorded as unresolved and left in place in reduced output.
"""
from __future__ import annotations

MISSING = object()


def is_local_ref(ref) -> bool:
    return isinstance(ref, str) and (ref == "#" or ref.startswith("#/"))


def is_external_ref(ref) -> bool:
    return isinstance(ref, str) and not is_local_ref(ref)


def pointer_parts(ref: str):
    """'#/components/schemas/Pet' -> ['components', 'schemas', 'Pet']."""
    if ref == "#":
        return []
    body = ref[2:] if ref.startswith("#/") else ref.lstrip("#")
    if not body:
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in body.split("/")]


def escape_part(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def make_pointer(parts) -> str:
    if not parts:
        return "#"
    return "#/" + "/".join(escape_part(str(p)) for p in parts)


def resolve(doc, ref: str):
    """Resolve a local ref against doc. Returns the node or MISSING."""
    node = doc
    for part in pointer_parts(ref):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return MISSING
    return node


def iter_refs(node, base_parts=()):
    """Yield (parts, ref) for every $ref at or below node.

    parts is the JSON-pointer path (as a list) of the object that
    carries the $ref, rooted at base_parts.
    """
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield list(base_parts), ref
        for key, value in node.items():
            yield from iter_refs(value, list(base_parts) + [key])
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            yield from iter_refs(value, list(base_parts) + [str(idx)])


def closure(doc, seeds):
    """Follow local $refs transitively from seed nodes.

    seeds: list of (parts, node) for subtrees of doc to start from.
    Returns (keep_pointers, unresolved) where keep_pointers is a set of
    canonical local pointer strings that were reached (including the
    seed subtrees' own pointers, which the caller supplies), and
    unresolved is a list of {"ref": ..., "from": pointer} for external
    refs encountered. Local refs that do not resolve in doc are also
    recorded in unresolved with a "missing_local" flag: they are broken
    in the source, and the reduced output cannot fix them.
    """
    keep = set()
    unresolved = []
    seen_unresolved = set()
    queue = [(list(parts), node) for parts, node in seeds]
    scanned = set()
    while queue:
        parts, node = queue.pop()
        marker = make_pointer(parts)
        if marker in scanned:
            continue
        scanned.add(marker)
        for ref_parts, ref in iter_refs(node, parts):
            if is_local_ref(ref):
                canon = make_pointer(pointer_parts(ref))
                if canon not in keep:
                    keep.add(canon)
                    target = resolve(doc, ref)
                    if target is MISSING:
                        key = (ref, make_pointer(ref_parts))
                        if key not in seen_unresolved:
                            seen_unresolved.add(key)
                            unresolved.append({
                                "ref": ref,
                                "from": make_pointer(ref_parts),
                                "missing_local": True,
                            })
                    else:
                        queue.append((pointer_parts(ref), target))
            else:
                key = (ref, make_pointer(ref_parts))
                if key not in seen_unresolved:
                    seen_unresolved.add(key)
                    unresolved.append({
                        "ref": ref,
                        "from": make_pointer(ref_parts),
                    })
    return keep, unresolved


def check_closure(doc):
    """Every local $ref in doc must resolve inside doc.

    Returns a list of failure strings (empty means closed). External
    refs are ignored here: they are unresolved by design, not broken.
    """
    failures = []
    for parts, ref in iter_refs(doc):
        if is_local_ref(ref) and resolve(doc, ref) is MISSING:
            failures.append(f"{make_pointer(parts)} -> {ref} does not resolve")
    return failures
