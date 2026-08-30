"""psyki.manifest — the capability manifest and the source registry.

Two files, two jobs, and the distinction is load-bearing.

`tool_manifest.json` holds **capabilities**. Canon §3 says a task *is* its
toolset, and `retinue.toolset_signature()` indexes cached agents by that
signature. So every tool in the manifest widens the task-type space, and a tool
version bump changes the identity of every task that uses it. That is the point:
a tool changing under a cached agent is a silent failure, and the signature is
what makes it loud.

`sources.json` holds **endpoints**. They are arguments to `net_fetch`, not
capabilities. If sources were tools, then "research against arXiv" and "research
against Crossref" would have different signatures, different retinue entries, and
two cached agents identical in behaviour. Adding a source must therefore be
invisible to the signature, and this module keeps it that way by never mixing the
two.

Nothing here reads the network, the clock, or the environment. Loading is pure
over the file contents, so a signature computed in CI equals one computed on the
host.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable
from urllib.parse import urlparse

MANIFEST_SCHEMA_VERSION: Final[str] = "2.0.0"
SOURCES_SCHEMA_VERSION: Final[str] = "2.0.0"

#: Trust classes. INTERNAL is the meta-agents, running inside the server under
#: the invariants. PROVISIONED is agents the server creates, running outside it
#: under a contract — already double-filtered by PSY's purpose and
#: AgentAgent's toolset, and bounded by a certificate KI can revoke. The
#: containment is the contract, which is why the provisioned tool list is the
#: wider of the two.
INTERNAL: Final[str] = "INTERNAL"
PROVISIONED: Final[str] = "PROVISIONED"

#: Reserved key carrying the trust class into the signature input.
#:
#: Canon §3 says a task is its toolset — but two toolsets holding identical
#: tools under different trust classes are not the same task. They get a
#: different agent, a different governing regime, and a different revocation
#: story. Without this the retinue would hand a cached provisioned agent to a
#: meta-agent request that happened to want the same tools, which is a
#: privilege crossing by way of a cache hit. `@` cannot appear in a tool name,
#: enforced at load, so the key cannot collide.
CLASS_KEY: Final[str] = "@trust_class"

MANIFEST_PATH: Final[str] = "tools/tool_manifest.json"
SOURCES_PATH: Final[str] = "tools/sources.json"


class ManifestError(Exception):
    """The manifest or the registry is malformed. Fail closed: a partially
    understood capability list is worse than none, because it silently narrows
    or widens what an agent may do."""


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    description: str
    effects: tuple[str, ...]
    classes: tuple[str, ...]

    def available_to(self, trust_class: str) -> bool:
        return trust_class in self.classes


@dataclass(frozen=True)
class Toolset:
    name: str
    purpose: str
    tools: tuple[str, ...]
    safety_ceiling: str
    trust_class: str


@dataclass(frozen=True)
class Source:
    """One endpoint.

    `enabled` and `constraints` are the reason this registry classifies rather
    than excludes. A source nobody should reach today is present, documented,
    and inert — which is strictly better than absent, because an absent source
    gets rediscovered and re-argued. A source with a real hazard carries a
    marker the policy layer enforces at the point of use, where the hazard
    actually lives.
    """

    id: str
    name: str
    base_url: str
    tier: str
    auth: str
    enabled: bool
    rate_limit: str
    cache_ttl_s: int
    fallback: str | None
    constraints: tuple[str, ...]

    @property
    def requires_key(self) -> bool:
        return self.auth != "NONE"

    def has(self, constraint: str) -> bool:
        return constraint in self.constraints


class Manifest:
    """Loaded capability manifest. Immutable after construction."""

    def __init__(self, tools: dict[str, Tool], toolsets: dict[str, Toolset],
                 severity: dict[str, int]) -> None:
        self._tools = tools
        self._toolsets = toolsets
        self._severity = severity

    # -- loading ---------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        raw = _read_json(path)
        _require_schema(raw, path, MANIFEST_SCHEMA_VERSION)

        severity = raw.get("effect_severity")
        if not isinstance(severity, dict) or not severity:
            raise ManifestError(f"{path}: effect_severity missing or empty")

        tools: dict[str, Tool] = {}
        for entry in raw.get("tools", []):
            tool = Tool(
                name=_require(entry, "name", path),
                version=_require(entry, "version", path),
                description=entry.get("description", ""),
                effects=tuple(entry.get("effects", ())),
                classes=tuple(entry.get("classes", ())),
            )
            if not tool.classes:
                raise ManifestError(
                    f"{path}: {entry.get('name')!r} declares no trust class"
                )
            if tool.name in tools:
                raise ManifestError(f"{path}: duplicate tool {tool.name!r}")
            if tool.name.startswith("@"):
                raise ManifestError(
                    f"{path}: tool name {tool.name!r} is reserved — '@' prefixes "
                    f"signature metadata and must not be a tool"
                )
            if not tool.effects:
                raise ManifestError(f"{path}: {tool.name!r} declares no effects")
            for effect in tool.effects:
                if effect not in severity:
                    raise ManifestError(
                        f"{path}: {tool.name!r} declares unknown effect {effect!r}"
                    )
            tools[tool.name] = tool

        if not tools:
            raise ManifestError(f"{path}: no tools declared")

        toolsets: dict[str, Toolset] = {}
        for entry in raw.get("toolsets", []):
            ts = Toolset(
                name=_require(entry, "name", path),
                purpose=entry.get("purpose", ""),
                tools=tuple(entry.get("tools", ())),
                safety_ceiling=_require(entry, "safety_ceiling", path),
                trust_class=_require(entry, "class", path),
            )
            if ts.name in toolsets:
                raise ManifestError(f"{path}: duplicate toolset {ts.name!r}")
            if not ts.tools:
                raise ManifestError(f"{path}: toolset {ts.name!r} is empty")
            for name in ts.tools:
                if name not in tools:
                    raise ManifestError(
                        f"{path}: toolset {ts.name!r} names unknown tool {name!r}"
                    )
                if not tools[name].available_to(ts.trust_class):
                    raise ManifestError(
                        f"{path}: {ts.trust_class} toolset {ts.name!r} names "
                        f"{name!r}, which is not available to that class — a "
                        f"meta-agent must not acquire a provisioned capability "
                        f"by way of a toolset"
                    )
            toolsets[ts.name] = ts

        if not toolsets:
            raise ManifestError(f"{path}: no toolsets declared")

        return cls(tools, toolsets, severity)

    # -- reads -----------------------------------------------------------

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    @property
    def toolset_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._toolsets))

    def toolsets_for(self, trust_class: str) -> tuple[str, ...]:
        return tuple(sorted(n for n, t in self._toolsets.items()
                            if t.trust_class == trust_class))

    def tools_for(self, trust_class: str) -> tuple[str, ...]:
        return tuple(sorted(n for n, t in self._tools.items()
                            if t.available_to(trust_class)))

    def tool(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ManifestError(f"unknown tool {name!r}") from None

    def toolset(self, name: str) -> Toolset:
        try:
            return self._toolsets[name]
        except KeyError:
            raise ManifestError(f"unknown toolset {name!r}") from None

    def versions(self, toolset_name: str) -> dict[str, str]:
        """`{tool_name: version}` for a named toolset.

        This is the exact shape `retinue.toolset_signature()` consumes, and it
        is the only intended way to reach it. Hand-assembling the dict elsewhere
        is how a version silently drops out of a signature.
        """
        ts = self.toolset(toolset_name)
        return {name: self._tools[name].version for name in ts.tools}

    def signature_input(self, toolset_name: str) -> dict[str, str]:
        """What the signature is actually computed over: the versioned tools
        plus the trust class. Use this, not `versions()`, wherever an agent is
        looked up or enrolled."""
        payload = self.versions(toolset_name)
        payload[CLASS_KEY] = self.toolset(toolset_name).trust_class
        return payload

    def declared_ceiling(self, toolset_name: str) -> str:
        return self.toolset(toolset_name).safety_ceiling

    def derived_ceiling(self, toolset_name: str) -> str:
        """The most severe effect any tool in the toolset carries.

        Declared and derived are kept separate on purpose. A declared ceiling
        that disagrees with the tools underneath it is the failure mode where a
        toolset looks safer than it is, and a test comparing the two is a gate
        that can actually fail.
        """
        ts = self.toolset(toolset_name)
        effects = {e for name in ts.tools for e in self._tools[name].effects}
        return max(effects, key=lambda e: self._severity[e])


class SourceRegistry:
    """Loaded egress allowlist. `net_fetch` consults this and nothing else."""

    def __init__(self, sources: dict[str, Source]) -> None:
        self._sources = sources

    @classmethod
    def load(cls, path: str | Path) -> "SourceRegistry":
        raw = _read_json(path)
        _require_schema(raw, path, SOURCES_SCHEMA_VERSION)

        sources: dict[str, Source] = {}
        for entry in raw.get("sources", []):
            src = Source(
                id=_require(entry, "id", path),
                name=entry.get("name", ""),
                base_url=_require(entry, "base_url", path),
                tier=_require(entry, "tier", path),
                auth=_require(entry, "auth", path),
                enabled=bool(entry.get("enabled", False)),
                rate_limit=entry.get("rate_limit", "unspecified"),
                cache_ttl_s=int(entry.get("cache_ttl_s", 0)),
                fallback=entry.get("fallback"),
                constraints=tuple(entry.get("constraints", ())),
            )
            if src.enabled and src.auth != "NONE":
                raise ManifestError(
                    f"{path}: {src.id!r} is enabled but needs {src.auth} — a "
                    f"credentialled source cannot be enabled in the committed "
                    f"registry, because the credential is not here"
                )
            if src.id in sources:
                raise ManifestError(f"{path}: duplicate source {src.id!r}")
            parsed = urlparse(src.base_url)
            if parsed.scheme != "https":
                raise ManifestError(
                    f"{path}: {src.id!r} base_url is not https — plaintext "
                    f"egress is a tamper path, not a convenience"
                )
            if not parsed.netloc:
                raise ManifestError(f"{path}: {src.id!r} base_url has no host")
            sources[src.id] = src

        for src in sources.values():
            if src.fallback is not None and src.fallback not in sources:
                raise ManifestError(
                    f"{path}: {src.id!r} falls back to unknown source "
                    f"{src.fallback!r}"
                )

        return cls(sources)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._sources))

    def get(self, source_id: str) -> Source:
        try:
            return self._sources[source_id]
        except KeyError:
            raise ManifestError(f"unknown source {source_id!r}") from None

    def by_tier(self, tier: str) -> tuple[Source, ...]:
        return tuple(s for s in self._sources.values() if s.tier == tier)

    def keyless(self) -> tuple[Source, ...]:
        return tuple(s for s in self._sources.values() if not s.requires_key)

    def enabled(self) -> tuple[Source, ...]:
        return tuple(s for s in self._sources.values() if s.enabled)

    def with_constraint(self, constraint: str) -> tuple[Source, ...]:
        return tuple(s for s in self._sources.values() if s.has(constraint))

    def time_witnesses(self) -> tuple[Source, ...]:
        """Sources that contribute a vote to the time quorum.

        Deliberately plural. A single unauthenticated reading is a value an
        attacker on the path chooses; a quorum across independent operators is
        something an attacker must own in aggregate. Note that these are only
        the *dedicated* witnesses — the Date header on every enabled source is
        also a vote, and is the larger part of the pool.
        """
        return tuple(s for s in self._sources.values()
                     if s.enabled and s.has("TIME_WITNESS"))

    def resolve(self, url: str, include_disabled: bool = False) -> Source | None:
        """The source that admits `url`, or None.

        Disabled sources are excluded by default: `resolve` answers "may this be
        fetched", and a documented-but-inert entry must never answer yes. Pass
        `include_disabled` to answer the different question "is this endpoint
        known", which is what tooling and audit want.

        Prefix match on the full canonical base URL, scheme and host and path
        together. Matching on host alone would admit any path on a shared host,
        and matching on a bare substring would admit an attacker-registered
        lookalike whose name contains an allowlisted one.
        """
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            return None
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        best: Source | None = None
        for src in self._sources.values():
            if not (src.enabled or include_disabled):
                continue
            base = src.base_url.rstrip("/")
            if canonical == base or canonical.startswith(base + "/"):
                if best is None or len(src.base_url) > len(best.base_url):
                    best = src
        return best

    def admits(self, url: str) -> bool:
        return self.resolve(url) is not None

    def fallback_chain(self, source_id: str) -> tuple[str, ...]:
        """`source_id` followed by its fallbacks, in order.

        Cycle-safe: a registry edited into a loop yields a truncated chain
        rather than hanging the fetch layer.
        """
        chain: list[str] = []
        seen: set[str] = set()
        current: str | None = source_id
        while current is not None and current not in seen:
            self.get(current)
            chain.append(current)
            seen.add(current)
            current = self._sources[current].fallback
        return tuple(chain)


# ------------------------------------------------------------------ helpers

def _read_json(path: str | Path) -> dict:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ManifestError(f"{p}: not found") from None
    except json.JSONDecodeError as e:
        raise ManifestError(f"{p}: invalid JSON — {e}") from None
    if not isinstance(data, dict):
        raise ManifestError(f"{p}: top level is not an object")
    return data


def _require_schema(raw: dict, path: str | Path, expected: str) -> None:
    version = raw.get("schema_version")
    if version != expected:
        raise ManifestError(
            f"{path}: schema_version {version!r}, expected {expected!r}"
        )


def _require(entry: dict, key: str, path: str | Path) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{path}: entry missing required {key!r}")
    return value


def load_all(
    root: str | Path = ".",
) -> tuple[Manifest, SourceRegistry]:
    """Load both files relative to a repo root."""
    base = Path(root)
    return (
        Manifest.load(base / MANIFEST_PATH),
        SourceRegistry.load(base / SOURCES_PATH),
    )


def signatures(manifest: Manifest, signer) -> dict[str, str]:
    """`{toolset_name: signature}` for every toolset.

    `signer` is `retinue.toolset_signature`, passed in rather than imported so
    this module stays free of a dependency it does not otherwise need.
    """
    return {name: signer(manifest.signature_input(name))
            for name in manifest.toolset_names}


def iter_effects(manifest: Manifest, names: Iterable[str]) -> set[str]:
    return {e for n in names for e in manifest.tool(n).effects}
