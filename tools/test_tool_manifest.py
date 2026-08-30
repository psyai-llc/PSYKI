"""Acceptance tests for the capability manifest and the source registry.

AGENTS.md §4a: every test here runs the behaviour. There is exactly one
existence check — `test_manifest_files_exist` — and it says so in its name,
because packaging presence is genuinely the property under test there.

Run standalone: python tests/test_tool_manifest.py
Or under pytest: python -m pytest tests/test_tool_manifest.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psyki import manifest as m  # noqa: E402
from psyki.retinue import toolset_signature  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load():
    return m.load_all(ROOT)


# ------------------------------------------------------------ structure

def test_manifest_files_exist():
    """Existence IS the property here — the loader has nothing to read
    otherwise. Named so it is not mistaken for a behavioural test."""
    assert (ROOT / m.MANIFEST_PATH).is_file()
    assert (ROOT / m.SOURCES_PATH).is_file()


def test_manifest_loads_and_is_populated():
    manifest, registry = _load()
    assert manifest.tool_names
    assert manifest.toolset_names
    assert registry.ids


def test_wrong_schema_version_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "bad_schema.json"
    p.write_text(json.dumps({"schema_version": "0.0.1", "tools": []}))
    try:
        m.Manifest.load(p)
    except m.ManifestError as e:
        assert "schema_version" in str(e)
    else:
        raise AssertionError("a wrong schema version must fail closed")


def test_malformed_json_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "bad_json.json"
    p.write_text("{ not json")
    try:
        m.Manifest.load(p)
    except m.ManifestError as e:
        assert "invalid JSON" in str(e)
    else:
        raise AssertionError("malformed JSON must fail closed")


# ------------------------------------------------------------ versioning

def test_every_tool_has_a_version():
    manifest, _ = _load()
    for name in manifest.tool_names:
        version = manifest.tool(name).version
        assert version, f"{name} has no version"
        assert version.count(".") == 2, f"{name} version {version!r} is not semver"


def test_versions_returns_the_shape_retinue_consumes():
    manifest, _ = _load()
    versions = manifest.versions("BUILD_VERIFY")
    assert isinstance(versions, dict)
    assert all(isinstance(k, str) and isinstance(v, str)
               for k, v in versions.items())
    assert toolset_signature(versions)


def test_signature_changes_when_a_tool_version_bumps():
    """The whole reason versions exist. A tool changing under a cached agent
    must change the signature, or the retinue serves a stale agent silently."""
    manifest, _ = _load()
    before = manifest.signature_input("BUILD_VERIFY")
    after = dict(before)
    del after[m.CLASS_KEY]
    victim = sorted(after)[0]
    after[victim] = "9.9.9"
    after[m.CLASS_KEY] = before[m.CLASS_KEY]
    assert toolset_signature(before) != toolset_signature(after)


def test_identical_tools_under_different_classes_differ():
    """META_READ and READ_ONLY hold the same tools. They are not the same task:
    different trust class, different agent, different governing regime. If they
    shared a signature the retinue would hand a cached provisioned agent to a
    meta-agent request — a privilege crossing by way of a cache hit."""
    manifest, _ = _load()
    a = manifest.signature_input("META_READ")
    b = manifest.signature_input("READ_ONLY")
    assert {k: v for k, v in a.items() if not k.startswith("@")} == \
           {k: v for k, v in b.items() if not k.startswith("@")}
    assert toolset_signature(a) != toolset_signature(b)


def test_toolsets_have_distinct_signatures():
    """Canon §3: the manifest partitions the task-type space. Two toolsets
    sharing a signature are one partition wearing two names."""
    manifest, _ = _load()
    sigs = m.signatures(manifest, toolset_signature)
    assert len(set(sigs.values())) == len(sigs), f"collision in {sigs}"


def test_signature_is_stable_across_reloads():
    a, _ = _load()
    b, _ = _load()
    for name in a.toolset_names:
        assert toolset_signature(a.signature_input(name)) == \
               toolset_signature(b.signature_input(name))


# ------------------------------------------------------------ referential integrity

def test_every_toolset_tool_is_declared():
    manifest, _ = _load()
    declared = set(manifest.tool_names)
    for ts_name in manifest.toolset_names:
        for tool in manifest.toolset(ts_name).tools:
            assert tool in declared, f"{ts_name} names undeclared {tool}"


def test_toolset_naming_unknown_tool_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "dangling.json"
    p.write_text(json.dumps({
        "schema_version": m.MANIFEST_SCHEMA_VERSION,
        "effect_severity": {"READ": 1},
        "tools": [{"name": "fs_read", "version": "1.0.0", "effects": ["READ"],
                   "classes": ["INTERNAL"]}],
        "toolsets": [{"name": "X", "tools": ["nope"], "safety_ceiling": "READ",
                      "class": "INTERNAL"}],
    }))
    try:
        m.Manifest.load(p)
    except m.ManifestError as e:
        assert "unknown tool" in str(e)
    else:
        raise AssertionError("a dangling tool reference must fail closed")


# ------------------------------------------------------------ safety ceilings

def test_declared_ceiling_matches_derived_ceiling():
    """A toolset that looks safer than the tools underneath it is the failure
    this catches. Declared is a claim; derived is the fact."""
    manifest, _ = _load()
    for name in manifest.toolset_names:
        assert manifest.declared_ceiling(name) == manifest.derived_ceiling(name), (
            f"{name} declares {manifest.declared_ceiling(name)} but its tools "
            f"reach {manifest.derived_ceiling(name)}"
        )


def test_read_only_toolset_cannot_write_execute_or_egress():
    manifest, _ = _load()
    effects = m.iter_effects(manifest, manifest.toolset("READ_ONLY").tools)
    assert effects == {"READ"}


def test_code_edit_cannot_execute_or_reach_the_network():
    manifest, _ = _load()
    effects = m.iter_effects(manifest, manifest.toolset("CODE_EDIT").tools)
    assert "EXECUTE" not in effects
    assert "EGRESS" not in effects


def test_research_cannot_write_or_execute():
    manifest, _ = _load()
    effects = m.iter_effects(manifest, manifest.toolset("RESEARCH").tools)
    assert "WRITE" not in effects
    assert "EXECUTE" not in effects


# ------------------------------------------------------------ source registry

def test_no_enabled_source_requires_a_credential():
    """The registry classifies rather than excludes, so keyed sources are
    listed. None of them may be enabled in the committed file — the credential
    is not in the repo, so an enabled keyed source is a fetch that fails at
    runtime instead of at load."""
    _, registry = _load()
    for src in registry.enabled():
        assert not src.requires_key, f"{src.id} is enabled but needs {src.auth}"


def test_enabled_keyed_source_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "enabled_keyed.json"
    p.write_text(json.dumps({
        "schema_version": m.SOURCES_SCHEMA_VERSION,
        "sources": [{"id": "x", "base_url": "https://x.example.com",
                     "tier": "COMMS", "auth": "API_KEY", "enabled": True}],
    }))
    try:
        m.SourceRegistry.load(p)
    except m.ManifestError as e:
        assert "enabled but needs" in str(e)
    else:
        raise AssertionError("an enabled credentialled source must fail closed")


def test_disabled_source_is_documented_but_not_fetchable():
    """The whole point of classification over exclusion: present, readable,
    inert."""
    _, registry = _load()
    disabled = [registry.get(i) for i in registry.ids if not registry.get(i).enabled]
    assert disabled, "expected some documented-but-inert sources"
    for src in disabled:
        assert not registry.admits(src.base_url + "/anything")
        assert registry.resolve(src.base_url + "/anything",
                                include_disabled=True) is not None


def test_time_quorum_has_enough_independent_witnesses():
    """Reducing time sources concentrates the attack surface rather than
    shrinking it. One reading is attacker-choosable; a quorum across distinct
    operators is not. The dedicated witnesses must at least reach the declared
    minimum on their own, before Date-header harvesting is counted."""
    _, registry = _load()
    policy = json.loads((ROOT / m.SOURCES_PATH).read_text())["time_policy"]
    witnesses = registry.time_witnesses()
    hosts = {w.base_url.split("/")[2] for w in witnesses}
    assert len(hosts) == len(witnesses), "two witnesses share a host — one vote, not two"
    assert policy["min_witnesses"] >= 3
    assert policy["harvest_date_headers"] is True, (
        "every HTTPS response already carries a Date header; not harvesting "
        "them discards the largest free source of independent witnesses"
    )


def test_elapsed_time_is_not_measured_by_the_quorum():
    """Quorum time answers what o'clock it is. Duration — the countdown, the
    lease, the grace window — is the monotonic clock's job, and conflating the
    two is what makes clock attacks work."""
    policy = json.loads((ROOT / m.SOURCES_PATH).read_text())["time_policy"]
    assert "monotonic" in policy["elapsed_time"].lower()


def test_insufficient_quorum_yields_unanchored_not_a_guess():
    policy = json.loads((ROOT / m.SOURCES_PATH).read_text())["time_policy"]
    assert "UNANCHORED" in policy["outlier_rule"]


def test_inference_sources_are_marked():
    """llm_prompt is a legitimate provisioned capability. The marker is not a
    ban — it records that this endpoint serves model inference, so the policy
    layer can keep it out of role binding, which TaskMaster owns."""
    _, registry = _load()
    for src in registry.by_tier("AI"):
        assert src.has("MODEL_INFERENCE"), src.id


def test_llm_prompt_is_provisioned_only():
    """A meta-agent acquiring arbitrary model access would let it rebind its own
    reasoning outside TaskMaster and outside binding_strength. A contracted
    agent using a model as a tool is a different thing entirely."""
    manifest, _ = _load()
    assert "llm_prompt" in manifest.tools_for(m.PROVISIONED)
    assert "llm_prompt" not in manifest.tools_for(m.INTERNAL)


def test_internal_toolsets_hold_no_provisioned_only_tool():
    manifest, _ = _load()
    for name in manifest.toolsets_for(m.INTERNAL):
        for tool in manifest.toolset(name).tools:
            assert manifest.tool(tool).available_to(m.INTERNAL), f"{name}/{tool}"


def test_internal_surface_is_smaller_than_provisioned():
    """The asymmetry is the design. Meta-agents run inside the invariants with
    nothing but the invariants constraining them. Provisioned agents are
    double-filtered before they exist and revocable after, so their tool list
    can be wide."""
    manifest, _ = _load()
    assert len(manifest.tools_for(m.INTERNAL)) < len(manifest.tools_for(m.PROVISIONED))


def test_every_tool_declares_a_trust_class():
    manifest, _ = _load()
    for name in manifest.tool_names:
        classes = manifest.tool(name).classes
        assert classes, name
        assert set(classes) <= {m.INTERNAL, m.PROVISIONED}, name


def test_toolset_naming_a_tool_outside_its_class_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "class_leak.json"
    p.write_text(json.dumps({
        "schema_version": m.MANIFEST_SCHEMA_VERSION,
        "effect_severity": {"READ": 1, "EGRESS": 4},
        "tools": [{"name": "llm_prompt", "version": "1.0.0",
                   "effects": ["READ", "EGRESS"], "classes": ["PROVISIONED"]}],
        "toolsets": [{"name": "META_X", "class": "INTERNAL",
                      "tools": ["llm_prompt"], "safety_ceiling": "EGRESS"}],
    }))
    try:
        m.Manifest.load(p)
    except m.ManifestError as e:
        assert "not available to that class" in str(e)
    else:
        raise AssertionError("a class leak through a toolset must fail closed")


def test_write_effect_sources_are_not_enabled():
    """net_fetch is GET-only. A source with real-world side effects stays inert
    until an explicit write path exists to carry it."""
    _, registry = _load()
    for src in registry.with_constraint("WRITE_EFFECT"):
        assert not src.enabled, f"{src.id} has WRITE_EFFECT and is enabled"


def test_constraints_use_the_declared_vocabulary():
    _, registry = _load()
    vocab = {"TIME_WITNESS", "MODEL_INFERENCE", "WRITE_EFFECT",
             "PII", "RATE_FRAGILE", "LICENCE_REVIEW", "COMPOUNDING"}
    for sid in registry.ids:
        for c in registry.get(sid).constraints:
            assert c in vocab, f"{sid} declares unknown constraint {c!r}"


def test_every_source_declares_a_known_tier():
    _, registry = _load()
    raw = json.loads((ROOT / m.SOURCES_PATH).read_text())
    tiers = set(raw["tiers"])
    for sid in registry.ids:
        assert registry.get(sid).tier in tiers, sid


def test_all_sources_are_https():
    _, registry = _load()
    for sid in registry.ids:
        assert registry.get(sid).base_url.startswith("https://"), sid


def test_plaintext_source_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "plaintext.json"
    p.write_text(json.dumps({
        "schema_version": m.SOURCES_SCHEMA_VERSION,
        "sources": [{"id": "x", "base_url": "http://example.com",
                     "tier": "REFERENCE", "auth": "NONE", "enabled": True}],
    }))
    try:
        m.SourceRegistry.load(p)
    except m.ManifestError as e:
        assert "https" in str(e)
    else:
        raise AssertionError("a plaintext base_url must fail closed")


def test_allowlist_admits_an_enabled_source():
    _, registry = _load()
    assert registry.admits("https://pypi.org/pypi/requests/json")


def test_allowlist_refuses_an_unlisted_host():
    _, registry = _load()
    assert not registry.admits("https://evil.example.com/payload")


def test_allowlist_refuses_a_lookalike_host():
    """Substring matching would admit this. Prefix matching on the full
    canonical base URL does not."""
    _, registry = _load()
    assert not registry.admits("https://pypi.org.evil.example.com/pypi/x")
    assert not registry.admits("https://notpypi.org/pypi/x")


def test_allowlist_refuses_plaintext_even_for_a_listed_host():
    _, registry = _load()
    assert not registry.admits("http://pypi.org/pypi/requests/json")


def test_allowlist_refuses_a_sibling_path_on_a_shared_host():
    """github_raw is allowlisted at a specific base. A different path on the
    same host is not automatically admitted."""
    _, registry = _load()
    assert registry.admits("https://raw.githubusercontent.com/o/r/main/f.py")
    assert not registry.admits("https://github.com/o/r/releases/download/x")


def test_resolve_returns_the_most_specific_source():
    _, registry = _load()
    src = registry.resolve("https://pypi.org/pypi/requests/json")
    assert src is not None and src.id == "pypi"


def test_fallback_chain_is_ordered_and_terminates():
    _, registry = _load()
    chain = registry.fallback_chain("osv")
    assert chain[0] == "osv"
    assert len(chain) == len(set(chain))


def test_fallback_to_unknown_source_fails_closed(tmp_path=None):
    p = Path(tmp_path or "/tmp") / "bad_fallback.json"
    p.write_text(json.dumps({
        "schema_version": m.SOURCES_SCHEMA_VERSION,
        "sources": [{"id": "a", "base_url": "https://a.example.com",
                     "tier": "REFERENCE", "auth": "NONE", "enabled": True,
                     "fallback": "ghost"}],
    }))
    try:
        m.SourceRegistry.load(p)
    except m.ManifestError as e:
        assert "unknown source" in str(e)
    else:
        raise AssertionError("a dangling fallback must fail closed")


def test_sources_do_not_appear_in_the_capability_manifest():
    """The separation that keeps the retinue from fragmenting. If a source id
    ever becomes a tool name, every task type that touches it splits."""
    manifest, registry = _load()
    assert not (set(manifest.tool_names) & set(registry.ids))


def test_adding_a_source_does_not_change_any_signature():
    """Stated as an executable claim rather than a comment: signatures are
    computed from the capability manifest alone, so the registry cannot
    influence them."""
    manifest, _ = _load()
    before = m.signatures(manifest, toolset_signature)
    registry_b = m.SourceRegistry.load(ROOT / m.SOURCES_PATH)
    assert registry_b.ids
    after = m.signatures(manifest, toolset_signature)
    assert before == after


# ------------------------------------------------------------ runner

def _main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items())
             if n.startswith("test_") and callable(o)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
        else:
            print(f"  pass  {name}")
    print(f"\n{'all green' if not failures else f'{failures} failed'} "
          f"({len(tests)} tests)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
