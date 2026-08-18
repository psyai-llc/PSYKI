# Neuromorphic Coding Techniques for Agentic AI and MCP Design: A Technical Assessment
## TL;DR
- Neuromorphic *coding* (sparse/event-driven representation, temporal codes, three-factor plasticity, predictive coding) is a load-bearing engineering framework for the agent **control plane**: demonstrable wins are energy/latency on always-on sensing (Xylo Audio 2: 6.6 µJ/inference, 291 µW dynamic power on keyword spotting; NorthPole: 25× more frames/joule than a V100 on ResNet-50), and these principles map cleanly onto MCP's already-event-driven substrate (notifications-as-spike-trains, subscriptions-as-synaptic-input).
- The highest-value, implementable transfers are: (1) integrate-and-fire notification gating with adaptive threshold + refractory period; (2) eligibility-trace credit assignment over tool trajectories; (3) basal-ganglia go/no-go tool gating with STN global stop; (4) neuromodulatory control of temperature/retry/model-tier; (5) SDR namespace routing; (6) predictive-coding delta-context. These are code today, not metaphor.
- Most neuroscience parallels are **evocative** until instrumented; the report labels each as established / extrapolation / speculation and gives falsifiable success criteria. Spiking hardware has NOT beaten dense GPU inference for LLM-scale transformer workloads and should not run the agent's policy model — the neuromorphic contribution is to the control plane, not the parameter-heavy generator.

## Key Findings

1. **Energy wins are real but domain-bounded.** On synaptic-operation accounting (the IBM TrueNorth/SynOps convention), the best neuromorphic processors reach thousands of GSOPs/W vs. hundreds of GFLOPs/W for GPUs, but the units are not commensurable. Per the systematic review *Neuromorphic Processing: The Future of Energy Efficient AI Computing* (Kitchenham method, 26 peer-reviewed articles 2015–2023): "the most efficient neuromorphic processor achieved 4,520 billion synaptic operations per watt (GSOPs/W), while the most efficient GPU achieved 365 billion floating-point operations per watt (GFLOPs/W)… not directly comparable due to fundamental differences between synaptic and floating-point operations." [ResearchGate](https://www.researchgate.net/publication/400886661_Neuromorphic_Processing_The_Future_of_Energy_Efficient_AI_Computing) Concrete measured wins are confined to keyword spotting, DVS vision, always-on sensing, and closed-loop control.

2. **MCP is already a spiking substrate in disguise.** JSON-RPC notifications are asynchronous, one-way, and event-triggered — structurally isomorphic to address-event representation (AER). `notifications/resources/updated`, `notifications/progress`, and `listChanged` are discrete events with no clock; the agent loop that consumes them can be made genuinely clock-free.

3. **Three control-theoretic transfers dominate the value.** (a) Neuromodulatory global gain (Aston-Jones & Cohen adaptive-gain; Yu & Dayan expected/unexpected uncertainty) → temperature/retry/model-tier control. (b) Basal-ganglia go/no-go/STN → tool gating and conflict-driven stop. (c) Eligibility traces / three-factor rules (e-prop, SuperSpike) → delayed credit assignment across multi-turn trajectories.

4. **Predictive coding gives a formal alternative to ReAct.** Active inference / expected-free-energy (EFE) action selection unifies exploration (epistemic value) and exploitation (pragmatic value) in one objective, replacing hand-tuned ReAct prompting heuristics with a principled policy posterior `Q(π) ∝ σ(−γ·G(π))`.

5. **Sparsity is the through-line.** Barlow efficient coding, the Attwell–Laughlin energy budget, and SDR mathematics all say the same thing: represent with the fewest active units, forward only prediction error, and pay only for surprise. This directly motivates token-economy strategies (delta-context, schema compression, context pruning).

## Details

### 1. Survey of neuromorphic coding techniques and efficacy

#### 1.1 Neural coding schemes
[ESTABLISHED] The coding scheme determines the spike budget and hence energy. Rate coding transmits information in mean firing rate over a window — robust but spike-expensive; most neuromorphic hardware supports it by default and it is "inefficient as a large number of spikes will be transmitted and processed during inference." [nih](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10198466/) Temporal / time-to-first-spike (TTFS) coding places all information in relative arrival time; "each neuron can only spike once during the entire inference process, and this results in high sparsity," [nih](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10198466/) cutting memory accesses and accelerator power. Rank-order coding (Thorpe) discards even the exact times, keeping only the permutation of first spikes — near-minimal spike count, capacity `log2(N!)` bits for N inputs. Phase coding references spike time to an oscillation (theta/gamma); population/vector coding (Georgopoulos; Eliasmith's Neural Engineering Framework) distributes a scalar/vector across a tuning-curve population, trading neuron count for precision and noise-robustness. Burst coding multiplexes a rate/timing channel. SDRs (Numenta) are the binary limit: a length-n vector with w≪n active bits.

| Scheme | Info capacity | Spike budget | Latency | Best fit |
|---|---|---|---|---|
| Rate | High, robust | Highest | High (window) | Noisy, hardware-default |
| TTFS/latency | Moderate | Lowest (1 spike/neuron) | Lowest | Feed-forward classification |
| Rank-order | `log2(N!)` | Very low | Low | Fast vision |
| Phase | High (multiplexed) | Moderate | Osc.-locked | Sequence/memory |
| Population/vector | Precision ∝ √N | Moderate–high | Low | Control, function rep. |
| SDR | `C(n,w)` states | Sparse binary | O(w) | Semantic routing |

[ESTABLISHED] SDR capacity/robustness math (Ahmad & Hawkins, *Properties of Sparse Distributed Representations*, arXiv:1503.07469): distinct-pattern capacity is the binomial `C(n,w)`; false-positive probability under a θ-of-w overlap match is closed-form. Verbatim worked example: "Suppose n=1024 and w=20. When storing M=20 vectors, the chance of a false positive when using perfect matches is about one in 5 billion… When θ=18, the chance increases to one in 4 million. However, if you increase n to 2048 with θ=18, the false positive rate drops dramatically to one in 223 billion!" [Numenta](https://www.numenta.com/assets/pdf/biological-and-machine-intelligence/BaMI-SDR.pdf) All matching operations are `O(w)`, independent of n.

#### 1.2 Learning rules
[ESTABLISHED] STDP is the two-factor Hebbian base (Δw depends on pre/post spike timing); variants add a triplet term, R-STDP adds a global reward third factor, voltage-dependent STDP conditions on postsynaptic depolarization. The credit-assignment problem in deep SNNs is solved by surrogate-gradient BPTT — SLAYER ("Spike Layer Error Reassignment in Time," Shrestha & Orchard, NeurIPS 2018) and SuperSpike (Zenke & Ganguli, *Neural Computation* 30(6):1514, 2018). SuperSpike "uses synaptic eligibility traces to solve the temporal credit assignment problem" [arXiv](https://arxiv.org/pdf/1901.09948) and is a forward-in-time three-factor rule not requiring BPTT. EventProp (Wunderlich & Pehle, *Sci. Rep.* 11, 2021) computes *exact* gradients through spike events. e-prop (Bellec et al., 2020) reformulates BPTT into a product of a local eligibility trace and a broadcast learning signal — "the learning signal … propagates the error directly back onto the neurons with a random weight, resembling the function of a neuromodulator." [arxiv](https://arxiv.org/pdf/2201.07602) Three-factor rules (Gerstner et al., *Front. Neural Circuits* 12:53, 2018) are the biological template for delayed-reward agent credit assignment. Forward-forward (Hinton) and predictive-coding networks (Rao & Ballard) provide backprop-free local alternatives.

#### 1.3 Neuron/network models
[ESTABLISHED] LIF is the workhorse: `τ_m dV/dt = −(V−V_rest) + R·I(t)`, spike+reset at threshold. ALIF adds an adaptive threshold/adaptation current (spike-frequency adaptation), materially improving temporal tasks. Izhikevich gives quadratic dynamics with rich firing regimes at low cost. Resonate-and-fire adds subthreshold oscillation. Reservoir computing / liquid state machines exploit fixed random recurrent dynamics with a trained readout; Legendre Memory Units give provably optimal continuous-delay memory. Spiking transformers: Spikformer (Zhou et al., ICLR 2023) introduces Spiking Self-Attention (SSA) with spike-form Q/K/V and no softmax; the Spike-Driven Transformer (Yao et al., NeurIPS 2023, arXiv:2307.01694) replaces the Q·K dot-product and softmax with mask+addition — Spike-Driven Self-Attention "exploits only mask and addition operations without any multiplication, and thus having up to 87.2× lower computation energy than vanilla self-attention… can achieve 77.1% top-1 accuracy on ImageNet-1K, which is the state-of-the-art result in the SNN field." [arxiv](https://arxiv.org/pdf/2507.10722) SpikeGPT replaces attention with a spiking RWKV; SpikingBERT/SpikeBERT adapt BERT. Reported: Spikformer ~11.577 mJ/image on ImageNet vs 38.340 mJ for the equivalent Transformer (~3.31×). [MDPI](https://www.mdpi.com/2079-9292/14/1/43)

#### 1.4 Homeostasis and stability
[ESTABLISHED] Synaptic scaling (Turrigiano) and intrinsic plasticity keep firing in a dynamic range; E/I balance and criticality (edge-of-chaos, neural avalanches with power-law size distributions) maximize dynamic range and information transmission. SHY (Tononi & Cirelli, *Brain Res. Bull.* 62:143, 2003; *Eur. J. Neurosci.* 51:413, 2020): wake potentiates synapses net-positive; sleep slow-wave activity renormalizes ("synaptic down-selection"), because "stronger synapses require more energy and supplies and are prone to saturation, creating the need for synaptic renormalization." [PubMed](https://pubmed.ncbi.nlm.nih.gov/30614089/) This is the biological warrant for offline consolidation/pruning passes.

#### 1.5 Hardware substrates — measured efficiency
[ESTABLISHED] Loihi (Davies et al., 2018): ~15 pJ per synaptic operation at nominal conditions, 30 GSOP/s. [arxiv](https://arxiv.org/pdf/1901.03690) Loihi 2 (Intel, 2021): up to 10× faster spike generation, sigma-delta/graded spikes; on PilotNet SDNN, 1.31 mJ/frame vs 21.94 mJ on Jetson Nano, latency 2.50 vs 5.77 ms (arXiv:2505.06417). [arxiv](https://arxiv.org/pdf/2505.06417) Static power per core ~30–80 mW; event-driven dynamic power only on spike/program events. [Emergent Mind](https://www.emergentmind.com/topics/intel-s-loihi-2-neuromorphic-chip)

Edge and research chips (conditions noted; vendor vs independent flagged):

| Chip | Metric | Value | Task / conditions | Source class |
|---|---|---|---|---|
| SynSense Xylo-Audio 2 | dyn. energy | 6.6 µJ/inf | "Aloha" KWS, 95% acc (Bos & Muir, arXiv:2406.15112) | vendor, measured |
| SynSense Xylo-Audio 2 | dyn. power | 291 µW | KWS, "best-in-class" | vendor, measured |
| SpiNNaker2 | dyn. power / energy | 7.1 mW / 7.1 µJ/inf | same KWS benchmark (Yan et al. 2021) | academic |
| SpiNNaker2 | synaptic event | ~10 pJ | LIF+STDP (Gonzalez et al. 2024) | academic |
| SpiNNaker2 MAC | efficiency | 6.4 TOPS/W | 8-bit, 250 MHz (Höppner, NICE) | academic |
| Loihi | KWS energy | 0.037–0.27 mJ/inf | Aloha KWS | academic |
| BrainChip Akida AKD1000 | energy | 37 µJ/inf | KWS, 4-bit | vendor claim |
| BrainChip Akida | latency | ~2 ms (8–9× vs Orin NX) | MNIST, batch 1 (ACM IoT 2025) | independent |
| SynSense Speck | active power | 8.74 mW | gesture recognition, DVS | vendor demo |
| SynSense Speck | event latency | 3.36 µs; <5 ms e2e | 9-layer sCNN | vendor |
| Innatera Pulsar | power | 400–600 µW | audio scene / radar presence | vendor claim |
| IBM NorthPole | efficiency | 25× frames/J vs V100; 5× vs H100 | ResNet-50 ImageNet (Modha et al., *Science* 382, adh1174, 2023) | IBM, peer-reviewed |
| IBM NorthPole (VPX board) | throughput | 40,300 fps → ~611 frames/J | ResNet-50, board-level (modha.org 2024) | IBM writeup |
| BrainScaleS-2 | total power | 175 mW | first-spike MNIST; idle≈active (Göltz/Cramer, *Nat. Mach. Intell.* 2021) | academic |
| ODIN (digital SNN ref.) | SOP energy | 12.7 pJ/SOP min | MNIST 15 nJ/inf (Frenkel, IEEE TBioCAS) | academic |

**Honest efficacy verdict** [ESTABLISHED]: neuromorphic wins decisively on always-on µW sensing (Xylo, Speck, Innatera), DVS vision (millisecond latency sub-watt), and small closed-loop control. NorthPole (a low-precision digital accelerator, *not* spiking) beats GPUs on ResNet-scale inference. No public result shows spiking hardware beating GPUs on LLM-scale autoregressive transformer inference — the regime that dominates agent cost.

Frameworks: Lava (Loihi 2), Nengo/NengoDL (NEF), snnTorch, Norse, BindsNET, SpikingJelly, Rockpool (SynSense). Surrogate-gradient training is available across snnTorch/Norse/SpikingJelly/SLAYER; ANN→SNN conversion across all.

#### 1.6 Energy-economy first principles
[ESTABLISHED] Attwell & Laughlin (*J. Cereb. Blood Flow Metab.* 21:1133, 2001): a rat cortical neuron firing at 4 Hz uses ~3.29×10⁹ ATP/s; budget ≈47% action potentials, 34% postsynaptic, 13% resting, 3% recycling. [arxiv](https://arxiv.org/pdf/2009.10615) An increase of 1 Hz mean rate costs ~6.5 µmol ATP/g/min. [SAGE Publications](https://journals.sagepub.com/doi/10.1097/00004647-200110000-00001) Levy & Baxter (*Neural Comp.* 8:531, 1996): distributed sparse codes minimize energy per bit. These are the biophysical statement of "compute only on surprise, represent sparsely" — the exact discipline a token-budgeted agent needs.

### 2. Direct application to agentic AI and MCP

#### 2.1 The clock-free agent
[EXTRAPOLATION] Standard ReAct loops poll: think→act→observe on a synchronous cadence. MCP's transport is already asynchronous — Streamable HTTP delivers server→client notifications over SSE; stdio is a bidirectional message stream. An event-driven agent blocks on an async notification queue and only "fires" (invokes the policy model) when accumulated evidence crosses a threshold. This is a literal LIF neuron over the notification stream (§4.1). Payoff: eliminates idle polling token/compute cost; latency bounded by event arrival, not poll interval.

#### 2.2 Sparsity and conditional computation
[EXTRAPOLATION] MoE routing is a coarse analogue of sparse neural activation: a gate selects k-of-N experts, exactly as k-winners-take-all selects active neurons. The transfer to agents: gate/threshold tool invocation (don't call a tool unless salience exceeds threshold), early-exit when confidence is high, skip-computation on low-error steps. The SDR union/overlap math bounds false-routes.

#### 2.3 Attention as resource allocation
[ESTABLISHED→EXTRAPOLATION] Thalamic gating via the pulvinar "regulates information transmission between cortical areas based on attention demands" (Saalmann et al., *Science* 337:753, 2012) through precision-weighted gain and priority maps; superior-colliculus saliency maps prioritize targets. Mapped to agents: context-window management is a priority map over candidate context items; a pulvinar-like router forwards only high-salience items to the (expensive) cortical model, gating by task-relevance. A 2026 Frontiers model even implements pulvinar pathways as learned skip-connections with gain-controlled gating (single-study, flagged as preliminary).

#### 2.4 Working memory, eligibility traces, credit assignment
[ESTABLISHED basis, EXTRAPOLATION to agents] Multi-turn tool use with delayed reward is the temporal-credit-assignment problem. e-prop's factorization — local eligibility trace `e_ij(t)` (decaying memory of pre/post coincidence) × delayed broadcast learning signal `L_j(t)` — is directly implementable over a tool-call trajectory: maintain a per-(state,tool) eligibility trace, and when terminal reward arrives, update selection propensities `Δθ ∝ Σ_t e_t · (R − b)`. This is TD(λ)/REINFORCE-with-eligibility in neuromorphic clothing, and it is exactly how DeepMind's prioritized experience replay (hippocampal-replay-inspired) improved DQN.

#### 2.5 Predictive coding / active inference as agent architecture
[ESTABLISHED theory] Active inference selects policies minimizing expected free energy `G(π) = −(pragmatic/utility value) − (epistemic/info-gain value)`, with policy posterior `Q(π) = σ(−γ G(π))`, γ a precision. This is a formal, single-objective replacement for ReAct's ad-hoc "reason then act": epistemic value *is* principled exploration (call the tool that most reduces uncertainty), pragmatic value *is* goal-seeking. Precision γ is a tunable temperature (§2.6, neuromodulation).

#### 2.6 MCP primitive → neuromorphic mappings
[EXTRAPOLATION] Grounded in the actual specs. The 2025-06-18 revision added structured tool output, elicitation, `resource_link`, OAuth Resource Server classification with RFC 8707 resource indicators, a required `MCP-Protocol-Version` header on subsequent HTTP requests, and removed JSON-RPC batching. [ForgeCode](https://forgecode.dev/blog/mcp-spec-updates/) The 2025-11-25 revision added experimental `tasks` for durable requests (polling/deferred retrieval, SEP-1686), icons metadata, tool-calling in sampling (`tools`/`toolChoice`, SEP-1577), URL-mode elicitation, and JSON Schema 2020-12 as the default dialect. [Modelcontextprotocol](https://modelcontextprotocol.info/specification/2025-11-25/changelog/) The 2026-07-28 release candidate deprecates Roots, Sampling, and Logging (advising tool parameters, direct provider APIs, and stderr/OpenTelemetry instead). [Hidekazu-konishi](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html)

| MCP primitive | Neuromorphic analogue | Optimization |
|---|---|---|
| `notifications/*` (one-way) | Spike / AER event | Event-driven loop; integrate-and-fire gating |
| `resources/subscribe` + `resources/updated` | Synaptic input channel | Threshold + refractory to prevent notification storms |
| `tools/list` + discovery | Synaptogenesis / developmental wiring | Capability negotiation = wiring; prune unused tools |
| `tools/call` | Action selection / motor output | Basal-ganglia go/no-go gate |
| Capability negotiation (`initialize`) | Critical-period wiring | Cache negotiated capability graph |
| Tool JSON Schema | Receptive field / tuning curve | SDR-compress schemas for O(w) routing |
| Context window | Cortical working memory | Predictive-coding delta-forwarding |
| `progress` / `tasks` (2025-11-25) | Tonic firing / sustained current | Backpressure via homeostatic rate control |
| Sampling (`tools`/`toolChoice`, 2025-11-25) | Cortico-thalamic loop | Precision-weighted output integration |
| Server mesh / multiplexing | Cortical areas + pulvinar hub | Saliency routing across servers |

### 3. Novel parallels from high-resolution neuroscience

[Labeling: E=established neuroscience, X=engineering extrapolation, S=speculation]

- **Canonical cortical microcircuit (E→X).** Laminar flow: L4 receives feedforward thalamic drive → L2/3 intracortical processing → L5 (driver output, subcortical) / L6 (modulator, corticothalamic feedback). The Sherman-Guillery driver/modulator distinction (L5 driver vs L6 modulator; *J. Neurosci.* 45:e1167242024) is anatomically explicit. **Map:** MCP host/client/server topology as a laminar hierarchy — clients = L4 input relays, host orchestration = L2/3, tool execution = L5 drivers, capability/feedback = L6 modulators. Cortico-thalamo-cortical loops via pulvinar = a routing hub multiplexing between servers on salience.
- **Neuromodulation as global control plane (E→X).** Dopamine = reward prediction error (Schultz); RPE → propensity updates. Acetylcholine = *expected* uncertainty, norepinephrine = *unexpected* uncertainty (Yu & Dayan, *Neuron* 46:681, 2005: "Acetylcholine signals expected uncertainty… Norepinephrine signals unexpected uncertainty, as when unsignaled context switches produce strongly unexpected observations"). [PubMed](https://pubmed.ncbi.nlm.nih.gov/15944135/) [Neuron](https://www.cell.com/neuron/fulltext/S0896-6273(05)00402-2) LC-NE adaptive gain: phasic mode = exploit, tonic mode = explore [SciSpace](https://scispace.com/papers/an-integrative-theory-of-locus-coeruleus-norepinephrine-2ljsj0k79l) (Aston-Jones & Cohen, *Annu. Rev. Neurosci.* 28:403, 2005). Serotonin = patience/time-horizon. **Map:** a `NeuromodulatoryController` sets sampling temperature (gain), retry budget, replan trigger (unexpected-uncertainty spike = network reset), and model-tier escalation. This is the single highest-ROI transfer.
- **Basal-ganglia action selection (E→X).** Direct (Go, D1, disinhibits thalamus), indirect (NoGo, D2, suppresses), hyperdirect (STN, fast global brake) pathways converge at GPi/SNr (Frank; eLife 08723). STN provides a conflict-driven global stop that raises the decision threshold. **Map:** tool-selection gate with Go/NoGo accumulators per candidate tool and an STN-style global stop when inter-tool conflict is high — measurably reduces false tool-invocation rate.
- **Hippocampal replay / SWR / consolidation (E→X).** Sharp-wave ripples tag and replay salient/novel experiences ~20× compressed for cortical consolidation; awake SWR replay content "provides a tagging mechanism to select aspects of experience that are preserved and consolidated for future use" [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC10659301/) (*Science* 2024, adk8261). Complementary-learning-systems → prioritized experience replay. **Map:** offline consolidation job compacts episodic agent logs into semantic memory, replaying high-reward/high-surprise trajectories preferentially.
- **Cerebellar forward models (E→S).** Marr-Albus-Ito: cerebellum learns internal forward models; climbing-fiber (inferior olive) delivers error signals. **Map:** a fast, cheap predictive cache / speculative tool-execution model whose mispredictions (climbing-fiber errors) trigger fallback to the expensive path — speculative execution with a verifier.
- **Astrocytes / tripartite synapse / glymphatic / SHY (E→S).** Sleep down-selects synapses; glymphatic clearance runs offline. **Map:** background "sleep pass" that prunes stale context, garbage-collects dead subscriptions, renormalizes tool-selection weights.
- **Immune system (E→S).** Innate (fast, pattern-based) vs adaptive (slow, specific, clonal memory) immunity; self/nonself + danger theory. **Map:** two-tier MCP security — innate layer = fast signature/heuristic prompt-injection filters on tool outputs; adaptive layer = learned per-server trust with memory of past attacks; danger signals = anomalous tool-output distributions.
- **Stigmergy / quorum sensing / Physarum (E→S).** Ant-colony pheromone trails, bacterial quorum thresholds, slime-mold network optimization solve distributed routing without central control. **Map:** multi-agent / server-mesh topology optimization — agents deposit "pheromone" (success weights) on server routes; quorum thresholds gate collective actions.
- **Efficient coding / FEP / metabolic budget (E→X).** Barlow redundancy reduction + Attwell-Laughlin budget + sparse coding = token economy. **Map:** cost-optimal agent design forwards only prediction error, represents context sparsely, pays only for surprise.
- **Self-organized criticality (E→S).** Operating at the edge of chaos maximizes dynamic range; **Map:** tune agent-swarm coupling to a critical regime (branching ratio ≈ 1) for maximal responsiveness without runaway cascades.
- **Precision-weighting (E→X).** Predictive processing weights prediction errors by inverse variance. **Map:** confidence-weighted integration of tool outputs — weight each tool result by estimated reliability before fusing.

### 4. Theorized optimizations with implementable code

All code targets CPython 3.11+, `numpy`, and the official `mcp` SDK (`mcp.server.fastmcp.FastMCP`). Each block is runnable and paired with verification methodology.

#### 4.1 Integrate-and-fire MCP notification gate (adaptive threshold + refractory)

```python
# lif_gate.py  — event-driven notification gating modeled on adaptive LIF
import time, math
from dataclasses import dataclass, field

@dataclass
class ALIFGate:
    """Adaptive leaky integrate-and-fire gate over an MCP notification stream.
    Fires (returns True -> wake the expensive policy model) when accumulated
    salient evidence crosses an adaptive threshold, outside the refractory period."""
    tau_m: float = 2.0          # membrane time constant (s): evidence leak
    v_thresh: float = 1.0       # base threshold
    theta_adapt: float = 0.0    # adaptive threshold increment (spike-freq. adaptation)
    tau_theta: float = 30.0     # adaptation decay (s)
    theta_gain: float = 0.5     # per-fire threshold bump
    refractory: float = 0.5     # refractory period (s)
    v: float = 0.0
    _t_last: float = field(default_factory=time.monotonic)
    _t_fire: float = -1e9

    def _decay(self, now: float) -> None:
        dt = now - self._t_last
        self.v *= math.exp(-dt / self.tau_m)
        self.theta_adapt *= math.exp(-dt / self.tau_theta)
        self._t_last = now

    def stimulate(self, salience: float, now: float | None = None) -> bool:
        """salience >= 0: weight of an incoming notification (e.g. inverse-variance
        precision * novelty). Returns True iff the gate fires."""
        now = now or time.monotonic()
        self._decay(now)
        if now - self._t_fire < self.refractory:
            return False                      # absolute refractory: drop the event
        self.v += salience
        if self.v >= self.v_thresh + self.theta_adapt:
            self._t_fire = now
            self.v = 0.0                       # reset
            self.theta_adapt += self.theta_gain
            return True
        return False
```

Wiring into a FastMCP client message handler (subscription = synaptic input, `resources/updated` = presynaptic spike):

```python
# The client accumulates resource-updated notifications; only escalates to the LLM
# when the ALIF gate fires, collapsing notification storms into salient wake events.
gate = ALIFGate()

async def on_resource_updated(uri: str, precision: float):
    if gate.stimulate(precision):
        await run_policy_model(reason=f"salient change at {uri}")
    # else: evidence integrated silently; no token spend
```

**Verification.** Baseline = poll-every-Δt or wake-on-every-notification. Metrics: (1) policy-model invocations per unit time (token/compute proxy), (2) missed-salient-event rate, (3) end-to-end reaction latency. Synthetic Poisson notification stream with injected salient bursts; sweep `v_thresh`, `refractory`. Falsifiable success: ≥50% invocation reduction at ≤5% missed-salient rate vs wake-on-every. Statistical validity: ≥30 seeds, report mean±95% CI, Mann–Whitney U vs baseline.

#### 4.2 Eligibility-trace credit assignment over tool trajectories

```python
# eligibility.py — three-factor (e-prop-style) credit assignment for tool selection
import numpy as np

class EligibilityCreditAssigner:
    def __init__(self, n_states: int, n_tools: int, lr=0.1, gamma=0.95, lam=0.8):
        self.theta = np.zeros((n_states, n_tools))  # selection logits
        self.e = np.zeros((n_states, n_tools))      # eligibility trace
        self.lr, self.gamma, self.lam = lr, gamma, lam

    def policy(self, s: int) -> np.ndarray:
        z = self.theta[s] - self.theta[s].max()
        p = np.exp(z); return p / p.sum()

    def act(self, s: int, rng=np.random) -> int:
        a = rng.choice(len(self.theta[s]), p=self.policy(s))
        grad = -self.policy(s); grad[a] += 1.0            # ∂logπ/∂θ  (local factor)
        self.e[s] += grad
        return a

    def decay(self):
        self.e *= self.gamma * self.lam

    def learn(self, reward: float, baseline: float = 0.0):
        rpe = reward - baseline                            # third (broadcast) factor
        self.theta += self.lr * rpe * self.e
```

**Toy task (testable).** Two-step tool chain where only the correct *pair* yields reward at the terminal step (delayed, sparse). Baseline = bandit updating only the last action. Success: eligibility agent reaches ≥95% optimal-pair rate in fewer episodes; ablate λ→0 to show the trace is load-bearing. Metric: episodes-to-threshold, regret curve, 20 seeds.

#### 4.3 Basal-ganglia go/no-go tool gate with STN global stop

```python
# bg_gate.py — direct/indirect/hyperdirect tool arbitration
import numpy as np

class BasalGangliaGate:
    def __init__(self, n_tools, thresh=1.0, stn_k=2.0, dt=0.05, leak=0.2):
        self.n=n_tools; self.thresh=thresh; self.stn_k=stn_k; self.dt=dt; self.leak=leak

    def select(self, go, nogo, max_t=200):
        """go, nogo: (n_tools,) evidence for facilitating/suppressing each tool.
        Returns index of selected tool or None (global stop)."""
        acc = np.zeros(self.n)
        for _ in range(max_t):
            conflict = self._conflict(acc)                 # STN reads co-activation
            drive = go - nogo - self.stn_k * conflict      # hyperdirect raises threshold
            acc += self.dt * (drive - self.leak * acc)
            acc = np.clip(acc, 0, None)
            if acc.max() >= self.thresh:
                return int(acc.argmax())
        return None                                        # no-go: inhibit all tools

    @staticmethod
    def _conflict(acc):
        s = np.sort(acc)[::-1]
        return s[1] if len(s) > 1 else 0.0                 # runner-up = conflict signal
```

**Metrics.** False tool-invocation rate (invoking a tool when none is appropriate — supply a "distractor" condition with all-low go), decision latency (iterations to threshold), and accuracy on a labeled tool-choice set. STN ablation (`stn_k=0`) should *increase* false invocations under high conflict — the falsifiable prediction. Report ROC over `thresh`.

#### 4.4 Neuromodulatory global controller

```python
# neuromod.py — RPE + expected/unexpected uncertainty -> temperature, retry, model tier
import numpy as np

class NeuromodController:
    def __init__(self, base_temp=0.7, kalman_q=0.01, kalman_r=0.1):
        self.temp=base_temp; self.mu=0.0; self.var=1.0
        self.q=kalman_q; self.r=kalman_r          # process / obs noise
        self.expected_unc=self.r; self.unexpected=0.0

    def update(self, reward):
        rpe = reward - self.mu                      # dopamine: reward prediction error
        k = self.var / (self.var + self.r)         # Kalman gain
        self.mu += k * rpe
        self.var = (1 - k) * self.var + self.q
        self.expected_unc = self.r                 # ACh: expected uncertainty
        self.unexpected = max(0.0, abs(rpe) - 2*np.sqrt(self.var + self.r))  # NE
        return rpe

    def controls(self):
        # NE tonic mode (high unexpected uncertainty) -> explore: raise temp, escalate tier
        temp = self.temp + 0.5*np.tanh(self.unexpected)
        retry_budget = int(1 + 3*np.tanh(self.expected_unc))
        model_tier = "large" if self.unexpected > 0.5 else "small"
        replan = self.unexpected > 0.75            # network reset / re-plan
        return dict(temperature=round(temp,3), retry_budget=retry_budget,
                    model_tier=model_tier, replan=replan)
```

**Verification.** Non-stationary bandit / tool-reliability environment with unsignaled context switches. Compare fixed-temperature vs neuromod controller on cumulative reward and tokens spent. Falsifiable: neuromod detects switches (unexpected-uncertainty spike) and triggers replan within N steps; ablate the NE term → slower recovery. Log `unexpected` as the "gain" (pupillometry-analogue) signal.

#### 4.5 SDR namespace routing for tools/resources

```python
# sdr_router.py — O(w) semantic routing of tool/resource namespaces
import numpy as np

class SDREncoder:
    def __init__(self, n=2048, w=40, seed=0):
        self.n, self.w = n, w
    def encode(self, text: str) -> np.ndarray:
        toks = text.lower().split()
        bits = set()
        per = max(1, self.w // max(1, len(toks)))
        for t in toks:
            h = np.random.default_rng(abs(hash(t)) % (2**32))
            bits.update(h.choice(self.n, size=per, replace=False).tolist())
        arr = np.zeros(self.n, dtype=np.uint8)
        idx = (list(bits)[:self.w]) or [0]
        arr[idx] = 1
        return arr

class SDRRouter:
    def __init__(self, theta=12):
        self.enc = SDREncoder(); self.entries = []       # (name, sdr)
        self.theta = theta
    def register(self, name, description):
        self.entries.append((name, self.enc.encode(name + " " + description)))
    def route(self, query):
        q = self.enc.encode(query)
        scored = [(name, int(np.dot(q, s))) for name, s in self.entries]  # O(w) overlap
        scored = [x for x in scored if x[1] >= self.theta]
        return sorted(scored, key=lambda x: -x[1])
```

**Verification.** Build from a real `tools/list`; query with paraphrases. Metrics: precision@1, false-positive rate vs θ (compare against the Ahmad–Hawkins closed form — recall n=1024, w=20, θ=18 gives a chance false-positive of ~1 in 4 million, and n=2048, θ=18 gives ~1 in 223 billion), routing latency vs a dense-embedding cosine baseline. Success: match embedding precision at lower latency/memory, with analytically bounded false-positive rate.

#### 4.6 Predictive-coding delta context manager

```python
# pc_context.py — forward only prediction error (delta), not full context
import difflib

class PredictiveContext:
    def __init__(self): self.model = ""              # server's belief of client context
    def forward(self, new_context: str) -> dict:
        sm = difflib.SequenceMatcher(a=self.model, b=new_context)
        deltas = [new_context[j1:j2] for tag,i1,i2,j1,j2 in sm.get_opcodes()
                  if tag in ("replace","insert")]
        payload = {"delta": deltas, "match_ratio": sm.ratio()}
        self.model = new_context                       # update generative model
        return payload
```

**Token-economy methodology.** Measure tokens transmitted (tokenizer-counted) full-context vs delta over a realistic multi-turn session with slowly-drifting context. Report % token reduction, reconstruction fidelity (client must rebuild exact context), and break-even (delta wins when inter-turn edit distance is small). Falsifiable: net token savings >X% at 100% reconstruction on sessions with match_ratio > 0.7.

#### 4.7 Hippocampal-replay consolidation job

```python
# consolidate.py — SWR-style prioritized compaction of episodic logs -> semantic memory
import numpy as np

def consolidate(episodes, summarizer, top_frac=0.2, novelty_key="surprise",
                reward_key="reward"):
    """Replay high-reward/high-surprise episodes preferentially (Science 2024 tagging).
    summarizer: callable(list[episode]) -> semantic_note."""
    if not episodes: return []
    pr = np.array([abs(e.get(reward_key,0)) + e.get(novelty_key,0) for e in episodes])
    pr = pr / (pr.sum() + 1e-9)
    k = max(1, int(top_frac*len(episodes)))
    idx = np.argsort(pr)[::-1][:k]                      # SWR tagging: salient subset
    return [summarizer([episodes[i]]) for i in idx]
```

**Verification.** Long-horizon task; compare downstream task accuracy / retrieval hit-rate with (a) no consolidation, (b) uniform-random compaction, (c) priority replay. Success: priority replay > random > none on retrieval-dependent tasks (mirrors PER > uniform in DQN). Metric: retrieval MRR, context size, task success.

#### 4.8 Homeostatic rate control / synaptic scaling for backpressure

```python
# homeostasis.py — synaptic-scaling analogue for MCP request budgeting
import random

class HomeostaticBudget:
    def __init__(self, target_rate=10.0, tau=5.0, gain=1.0):
        self.target=target_rate; self.tau=tau; self.gain=gain
        self.scale=1.0; self.rate_est=target_rate; self._t=None
    def admit(self, now, cost=1.0) -> bool:
        if self._t is not None:
            dt = now - self._t
            self.rate_est += (-self.rate_est*dt/self.tau)   # leaky rate estimate
        self._t = now
        # intrinsic-plasticity style multiplicative renormalization
        self.scale *= (self.target / max(self.rate_est,1e-3))**(self.gain*0.01)
        self.scale = min(max(self.scale, 0.05), 1.0)
        if random.random() < self.scale:
            self.rate_est += cost; return True
        return False                                       # backpressure drop/defer
```

**Verification.** Bursty request load; measure served-rate stability around target, drop rate, and tail latency vs a token-bucket baseline. Success: lower rate variance and no server saturation; the multiplicative scaling should converge (Turrigiano synaptic-scaling analogue).

#### 4.9 Astrocyte-inspired sleep/pruning pass
Combine §4.7 (consolidate) + a GC sweep of stale subscriptions + §4.8 weight renormalization, run on an idle timer (SHY "sleep pass"). Verification: long-running agent memory footprint and stale-subscription count over time with vs without the pass; success = bounded memory, no accuracy regression.

### 5. Final synthesis

#### 5.1 Unified design schema (text architecture)

```
                         ┌─────────────────────────────────────────┐
                         │   NEUROMODULATORY CONTROL PLANE (§4.4)   │
                         │  DA(RPE) ACh(exp-unc) NE(unexp-unc) 5-HT │
                         │  -> temperature, retry, model-tier,      │
                         │     replan/reset, precision γ            │
                         └───────────────┬─────────────────────────┘
                                         │ global gain / gating signals
  MCP servers (L5 drivers)               ▼
  ┌──────────┐  notifications   ┌───────────────────┐   salient wake  ┌──────────┐
  │ server A │ ───spike train──▶│  ALIF NOTIFICATION │────────────────▶│  POLICY  │
  │ server B │ ───AER events───▶│  GATE (§4.1)       │                 │  MODEL   │
  │ server C │                  │  +refractory/adapt │                 │ (cortex) │
  └────┬─────┘                  └─────────┬──────────┘                 └────┬─────┘
       │ tools/list                       │ integrated evidence              │ action
       ▼                                  ▼                                  ▼
  ┌──────────┐   overlap route   ┌───────────────────┐   go/nogo/stop  ┌──────────┐
  │ SDR      │◀─────────────────▶│  PULVINAR ROUTER  │────────────────▶│ BASAL-   │
  │ NAMESPACE│                   │  saliency/priority│                 │ GANGLIA  │
  │ (§4.5)   │                   │  map over servers │                 │ GATE(§4.3)│
  └──────────┘                   └───────────────────┘                 └────┬─────┘
                                                                            │ tools/call
  ┌───────────────────────────────────────────────────────────────────────┼────────┐
  │ MEMORY SUBSYSTEM                                                        ▼        │
  │  eligibility traces (§4.2) ── credit ──▶ semantic memory ◀── replay consolidation│
  │  predictive-context delta (§4.6)          (§4.7, hippocampal SWR)                │
  │  homeostatic budget (§4.8) ── backpressure     astrocyte sleep pass (§4.9)       │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

**Component contracts (interfaces).**
- `Gate.stimulate(salience: float) -> bool` (idempotent per event; monotonic time).
- `Router.route(query: str) -> list[(name, overlap:int)]` (pure; O(w)).
- `BG.select(go, nogo) -> int | None` (None = inhibit).
- `Neuromod.update(reward) -> rpe; .controls() -> dict` (side-effect-free read).
- `Credit.act(s)->a; .learn(reward)` (trace mutation localized).
- Event schema (JSON): `{"uri":str,"kind":"resources/updated","precision":float,"ts":float}`.
- Reward/telemetry schema: `{"episode":str,"reward":float,"surprise":float,"tools":[...]}`.

#### 5.2 Coding style guide (operationalizing the principles)
- **Event-first, clock-never.** No polling loops. All I/O is `async`; components block on queues. Every module exposes an `async def on_event(evt)`; nothing wakes the policy model except a gate firing.
- **Sparsity discipline.** Prefer binary/SDR representations for routing; forward deltas not full state (§4.6); enforce a token budget as a hard resource (Attwell–Laughlin discipline: pay only for surprise).
- **Three-factor separation.** Keep *local* state (eligibility traces, membrane potentials) separate from *global* signals (reward, neuromodulators). Local updates are pure functions of local state plus a single broadcast scalar. Name them `e_*` (eligibility), `v_*` (potential), `mod_*` (neuromodulator).
- **Typing/contracts.** Full type hints; `dataclass` for neuron/gate state; numeric state in `numpy` arrays with documented shapes `(n_tools,)`. All thresholds and time-constants are named constants with units in the docstring (`tau_m` in seconds).
- **Falsifiability by construction.** Every neuromorphic component ships with an ablation flag (`stn_k=0`, `lam=0`, `theta_gain=0`) so its contribution is measurable. No component is merged without a benchmark-harness entry.
- **Module layout.** `gates/` (ALIF, BG), `control/` (neuromod), `routing/` (SDR, pulvinar), `memory/` (eligibility, replay, pc_context), `homeostasis/`, `harness/` (benchmarks). One concept per module; no cross-imports except through typed interfaces.

#### 5.3 Phased roadmap with success criteria
- **Phase 0 (instrument):** wrap an existing ReAct MCP agent with telemetry (invocations, tokens, latency, tool-error rate). Baseline everything. *Exit:* reproducible metric pipeline, ≥30-seed CI.
- **Phase 1 (event loop + gating):** deploy ALIF notification gate (§4.1) + homeostatic budget (§4.8). *Success:* ≥50% fewer policy invocations at ≤5% missed-salient; stable served-rate.
- **Phase 2 (selection):** basal-ganglia gate (§4.3) + SDR router (§4.5). *Success:* measurable drop in false tool-invocation rate; routing precision ≥ embedding baseline at lower latency. *Ablation:* STN off, θ sweep.
- **Phase 3 (control + credit):** neuromod controller (§4.4) + eligibility traces (§4.2). *Success:* higher cumulative reward / lower tokens on non-stationary tasks; faster context-switch recovery. *Ablation:* NE term off, λ=0.
- **Phase 4 (memory):** predictive-context delta (§4.6) + replay consolidation (§4.7) + sleep pass (§4.9). *Success:* token reduction at 100% reconstruction; bounded memory; retrieval MRR ↑.
- **Phase 5 (predictive-coding agent):** replace ReAct policy with EFE action selection (§2.5). *Success:* matches or beats ReAct task success with principled exploration and no hand-tuned heuristics.
- **Reference test harness:** synthetic MCP servers emitting controllable notification streams with injected salience/novelty/reward; non-stationary tool-reliability environment; long-horizon retrieval task. Report mean±95% CI, non-parametric tests, ablations per component.

## Recommendations
1. **Adopt now (high ROI, low risk):** event-driven loop with ALIF gating (§4.1), neuromodulatory temperature/retry/tier control (§4.4), and predictive-coding delta-context (§4.6). These are pure control-plane wins with immediate token/latency payoff and clean ablations. Threshold to proceed to Phase 2: ≥40% invocation reduction sustained over a week of real traffic.
2. **Pilot next:** basal-ganglia tool gating (§4.3) and SDR routing (§4.5) once you have >~15 tools per server, where false-invocation and routing latency start to bite. Change trigger: if precision@1 of embedding routing <0.9 or routing latency dominates, ship SDR.
3. **Defer until scale demands:** replay consolidation and sleep passes (§4.7, §4.9) matter only for long-running/persistent agents; adopt when session memory exceeds context budget.
4. **Do NOT** put spiking hardware in the LLM inference path — no evidence supports it at transformer scale. Use neuromorphic *principles* in software; reserve actual neuromorphic silicon (Xylo/Speck/Akida/Loihi) for genuinely always-on edge sensing feeding the agent.
5. **Instrument for falsifiability:** never ship a bio-inspired component without its ablation flag and a harness entry. A parallel that cannot be turned off and measured is metaphor, not engineering.

## Caveats
- **Load-bearing vs evocative.** Load-bearing (measurable engineering value, established mechanism): eligibility traces, neuromodulatory gain control, go/no-go gating, SDR math, efficient-coding/token-economy, event-driven gating. Evocative-until-instrumented (plausible but unproven transfer): pulvinar routing, cerebellar speculative caches, astrocyte GC, immune security tiers, stigmergy mesh, self-organized criticality. The distinguishing evidence in every case is the ablation study in §5.3 — if turning the component off doesn't degrade a metric, it was metaphor.
- **Unit incommensurability.** GSOPs/W vs GFLOPs/W, and per-"inference" energy where "inference" differs per chip (Xylo = 10 timesteps, NorthPole = 1 frame, Akida = 1 image/keyword), are not directly comparable. All hardware numbers are reported with source class (vendor claim vs independent) and conditions; several edge figures (Speck, Innatera) are vendor marketing lacking independent peer review.
- **Speculative-verb hygiene.** Where sources use "could"/"may"/projections (e.g., pulvinar-as-skip-connection is a single 2026 Frontiers model; NorthPole comparisons are IBM-authored though peer-reviewed in *Science*), this is flagged; these are not presented as settled agent-engineering results.
- **Corpus gap.** The intended `psyai-llc/psyki/corpus` standard could not be consulted; terminology and technique choices here follow mainstream literature and may diverge from that corpus's conventions.
- **Spiking transformers are vision-scale.** Spikformer / Spike-Driven Transformer energy claims (up to 87.2× MAC-energy reduction, ~3.31× vs Transformer) are on ImageNet-class vision at T=4, with residual accuracy gaps; they are not evidence for LLM-scale spiking agents.
