import time
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="MongoDB AI Brain Simulator",
    page_icon="🧠",
    layout="wide",
)

MONGO_GREEN = "#00ED64"
DARK = "#06110B"
CARD = "#0D1F16"
SOFT = "#E9FFF1"

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #06110B 0%, #0B1F16 45%, #020604 100%);
}

/* Only style our custom HTML, not every Streamlit element */
.hero {
    padding: 34px;
    border-radius: 28px;
    background: linear-gradient(135deg, rgba(0,237,100,.22), rgba(0,0,0,.35));
    border: 1px solid rgba(0,237,100,.35);
    box-shadow: 0 0 45px rgba(0,237,100,.18);
    margin-bottom: 24px;
}

.hero-title {
    font-size: 56px;
    font-weight: 900;
    color: white;
    line-height: 1;
}

.hero-sub {
    margin-top: 16px;
    font-size: 20px;
    color: #C8FFD8;
    max-width: 1050px;
}

.brain-card {
    padding: 22px;
    border-radius: 22px;
    background: #0D1F16;
    border: 1px solid rgba(0,237,100,.35);
    box-shadow: 0 0 26px rgba(0,237,100,.12);
    min-height: 170px;
}

.brain-title {
    color: #00ED64;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 8px;
}

.brain-body {
    color: #E9FFF1;
    font-size: 15px;
}

.pill {
    display: inline-block;
    padding: 6px 10px;
    margin: 8px 5px 0 0;
    border-radius: 999px;
    color: #C8FFD8;
    background: rgba(0,237,100,.12);
    border: 1px solid rgba(0,237,100,.30);
    font-size: 12px;
}

.pg-card {
    padding: 18px;
    border-radius: 18px;
    background: #1F1111;
    border: 1px solid rgba(255,80,80,.35);
    min-height: 135px;
}

.pg-title {
    color: #FF8080;
    font-weight: 800;
    font-size: 18px;
}

.pg-body {
    color: #FFECEC;
    font-size: 14px;
}

.big-number {
    font-size: 54px;
    font-weight: 900;
    color: #00ED64;
}

.caption-green {
    color: #C8FFD8;
    font-size: 15px;
}
</style>
""", unsafe_allow_html=True)


def dark_plot(fig, height=450):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=SOFT),
        margin=dict(l=30, r=30, t=50, b=30),
    )
    return fig


DOCUMENTS = {
    "intent_registry": {
        "_id": "intent_contract_review",
        "label": "contract_review",
        "description": "User wants to review, redline, or summarize a contract",
        "confidence_threshold": 0.82,
        "routing": {
            "primary_model": "anthropic-claude-3-5",
            "fallback_model": "openai-gpt-4o",
            "prompt_template_id": "tmpl_contract_review_v2",
            "tools_enabled": ["vector_search", "pdf_parser", "citation_extractor"]
        },
        "rag_config": {
            "collection": "contract_embeddings",
            "top_k": 8,
            "similarity_metric": "cosine",
            "min_score": 0.75
        },
        "guardrails": {
            "pii_redaction": True,
            "max_output_tokens": 4096,
            "content_filter": "legal_safe"
        }
    },
    "prompt_templates": {
        "_id": "tmpl_contract_review_v2",
        "name": "contract_review",
        "version": 2,
        "variants": {
            "openai-gpt-4o": {
                "system": "You are a precise contract analyst.",
                "user_template": "Review this contract and cite risky clauses: {{document}}"
            },
            "anthropic-claude-3-5": {
                "system": "Analyze the contract for risk, obligation, and ambiguity.",
                "user_template": "<contract>{{document}}</contract>"
            },
            "llama-3-70b": {
                "prompt_template": "[INST] Review contract risk: {{document}} [/INST]"
            }
        },
        "tags": ["contracts", "rag", "production"]
    },
    "model_config": {
        "_id": "cfg_production_2026_q1",
        "active": True,
        "primary": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "temperature": 0.2,
            "max_tokens": 8192
        },
        "fallback": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.2,
            "max_tokens": 8192
        },
        "cost_controls": {
            "monthly_budget_usd": 5000,
            "per_request_cap_usd": 0.50,
            "alert_threshold_pct": 80
        }
    },
    "session_memory": {
        "_id": "sess_a1b2c3d4",
        "user_id": "usr_9912",
        "model": "claude-3-5-sonnet",
        "context_window_tokens": 8192,
        "turns": [
            {
                "role": "user",
                "content": "Review this contract for termination risk.",
                "embedding_ref": "emb_001"
            },
            {
                "role": "assistant",
                "content": "The termination language gives the vendor broad discretion.",
                "tokens_used": 312,
                "embedding_ref": "emb_002"
            }
        ],
        "metadata": {
            "session_type": "contract_review",
            "source_doc_ids": ["doc_msa_2026"],
            "user_tier": "enterprise"
        }
    },
    "feedback_loop": {
        "_id": "eval_contract_review_2026_01",
        "application": "contract_review_agent",
        "success_criteria": {
            "retrieval_relevance": 0.90,
            "answer_correctness": 0.88,
            "citation_quality": 0.92,
            "task_completion": 0.85
        },
        "signals": [
            "thumbs_up_down",
            "human_review",
            "citation_clicks",
            "escalations",
            "abandoned_sessions"
        ],
        "last_tuning_action": {
            "changed": "rag_config.top_k",
            "from": 5,
            "to": 8,
            "reason": "Improve recall on long contracts"
        }
    }
}


st.markdown("""
<div class="hero">
  <div class="hero-title">MongoDB AI Brain Simulator</div>
  <div class="hero-sub">
    Postgres stores records. MongoDB stores the intelligence layer:
    prompts, memory, intent routing, model config, vector context, and feedback loops.
  </div>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Schema migrations", "0", "for model swaps")
m2.metric("AI brain collections", "5", "native documents")
m3.metric("Runtime changes", "Documents", "not deployments")
m4.metric("Feedback loop", "Built in", "continuous tuning")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 AI Brain Run",
    "🍝 Postgres Pain",
    "🍃 MongoDB Intelligence Layer",
    "🚀 Model Evolution"
])


with tab1:
    st.subheader("Watch an AI request move through the MongoDB brain")

    user_prompt = st.text_input(
        "User request",
        value="Review this contract and identify termination risk."
    )

    run = st.button("Run AI Brain Simulation", type="primary")

    steps = [
        ("Intent identified", "intent_registry", "contract_review detected with confidence 0.91"),
        ("Prompt selected", "prompt_templates", "Loaded model-specific contract review prompt"),
        ("Model config loaded", "model_config", "Primary: Claude 3.5 Sonnet. Fallback: GPT-4o"),
        ("Memory hydrated", "session_memory", "Loaded prior user context and source documents"),
        ("Vector context retrieved", "context_chains", "Top 8 relevant clauses retrieved with scores"),
        ("Response generated", "LLM", "Answer generated with citations and risk ranking"),
        ("Feedback captured", "feedback_loop", "Signal stored for future tuning"),
    ]

    if run:
        progress = st.progress(0)
        status_box = st.empty()

        for i, (name, collection, detail) in enumerate(steps, start=1):
            progress.progress(i / len(steps))
            status_box.success(f"✓ {name}: {detail}")
            time.sleep(0.35)

        st.divider()
        st.subheader("Generated response")

        st.markdown(f"""
        **Request:** {user_prompt}

        **Answer:** The highest termination risk is the vendor's unilateral termination clause.
        It allows termination with limited notice and does not clearly define cure rights.

        **Why it matters:** In production, the app did not hard-code this behavior.
        It loaded routing, prompts, model settings, memory, and feedback criteria from MongoDB documents.
        """)

        st.subheader("MongoDB document used during this step")
        selected = st.selectbox("Inspect document", list(DOCUMENTS.keys()))
        st.json(DOCUMENTS[selected])

    else:
        st.info("Click the button to simulate the AI brain runtime.")


with tab2:
    st.subheader("The relational version gets ugly fast")

    c1, c2, c3 = st.columns(3)

    tables = [
        ("prompt_templates", "Stores base prompt names"),
        ("prompt_template_versions", "One row per version"),
        ("prompt_model_variants", "One row per model-specific prompt shape"),
        ("model_configs", "Provider, model, temperature, limits"),
        ("routing_rules", "Intent-to-model routing"),
        ("rag_configs", "Top-k, score thresholds, collections"),
        ("memory_sessions", "Conversation session header"),
        ("memory_turns", "One row per turn"),
        ("feedback_events", "One row per signal"),
    ]

    for idx, (title, body) in enumerate(tables):
        target_col = [c1, c2, c3][idx % 3]
        target_col.markdown(f"""
        <div class="pg-card">
          <div class="pg-title">{title}</div>
          <div class="pg-body">{body}<br><br>⚠ migration / join / deploy risk</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    df = pd.DataFrame({
        "Change": [
            "Add new model prompt shape",
            "Add per-intent guardrails",
            "Store variable memory turns",
            "Add feedback signal",
            "Change RAG strategy",
            "Swap primary/fallback model"
        ],
        "Postgres impact": [
            "New columns or variant tables",
            "ALTER TABLE or new join table",
            "Unbounded child rows",
            "New event schema",
            "Config table changes",
            "Code + table update"
        ],
        "Operational drag": [8, 7, 6, 6, 7, 8]
    })

    fig = go.Figure(go.Bar(
        x=df["Operational drag"],
        y=df["Change"],
        orientation="h",
        text=df["Postgres impact"],
        textposition="auto",
    ))

    fig.update_layout(
        title="Relational drag as AI systems evolve",
        xaxis_title="Pain level",
        yaxis_title="",
    )

    st.plotly_chart(dark_plot(fig, 500), use_container_width=True)


with tab3:
    st.subheader("MongoDB stores the AI system as flexible documents")

    c1, c2, c3 = st.columns(3)

    cards = [
        ("intent_registry", "Routes user intent to strategy, model, prompt, tools, RAG config, and guardrails.", ["routing", "tools", "guardrails"]),
        ("prompt_templates", "Stores different prompt structures per model without schema changes.", ["OpenAI", "Claude", "Llama"]),
        ("model_config", "Controls active model, fallback model, cost caps, temperature, and limits.", ["primary", "fallback", "budget"]),
        ("session_memory", "Persists rolling conversation state, turns, metadata, and embeddings.", ["turns[]", "tokens", "metadata"]),
        ("context_chains", "Tracks retrieved chunks, similarity scores, citations, and generated responses.", ["RAG", "vectors", "citations"]),
        ("feedback_loop", "Stores evaluation metrics, user signals, human review, and tuning history.", ["evals", "signals", "tuning"]),
    ]

    for idx, (title, body, pills) in enumerate(cards):
        target_col = [c1, c2, c3][idx % 3]
        pill_html = "".join([f'<span class="pill">{p}</span>' for p in pills])
        target_col.markdown(f"""
        <div class="brain-card">
          <div class="brain-title">{title}</div>
          <div class="brain-body">{body}</div>
          <br>
          {pill_html}
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    selected = st.selectbox("Open a MongoDB document", list(DOCUMENTS.keys()))
    st.json(DOCUMENTS[selected])


with tab4:
    st.subheader("Model evolution without schema migration drama")

    before, after = st.columns(2)

    with before:
        st.markdown("### Before")
        st.json(DOCUMENTS["model_config"])

    updated_config = json.loads(json.dumps(DOCUMENTS["model_config"]))
    updated_config["primary"] = {
        "provider": "openai",
        "model": "gpt-5",
        "temperature": 0.2,
        "max_tokens": 128000
    }
    updated_config["fallback"] = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet",
        "temperature": 0.2,
        "max_tokens": 8192
    }
    updated_config["effective_date"] = "2026-06-10T00:00:00Z"

    with after:
        st.markdown("### After")
        st.json(updated_config)

    st.divider()

    a, b, c = st.columns(3)
    a.markdown('<div class="big-number">0</div><div class="caption-green">DDL changes</div>', unsafe_allow_html=True)
    b.markdown('<div class="big-number">0</div><div class="caption-green">schema migrations</div>', unsafe_allow_html=True)
    c.markdown('<div class="big-number">1</div><div class="caption-green">document update</div>', unsafe_allow_html=True)

    timeline = pd.DataFrame({
        "Model": ["GPT-4", "Claude 3", "GPT-4o", "Voyage", "GPT-5", "Future Model"],
        "MongoDB change": [1, 1, 1, 1, 1, 1],
        "Postgres change": [4, 5, 6, 5, 8, 9],
    })

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timeline["Model"],
        y=timeline["MongoDB change"],
        mode="lines+markers",
        name="MongoDB document updates",
        line=dict(width=4)
    ))
    fig.add_trace(go.Scatter(
        x=timeline["Model"],
        y=timeline["Postgres change"],
        mode="lines+markers",
        name="Postgres schema/app changes",
        line=dict(width=4)
    ))

    fig.update_layout(
        title="AI model changes over time",
        yaxis_title="Operational change required",
        xaxis_title="",
    )

    st.plotly_chart(dark_plot(fig, 460), use_container_width=True)
