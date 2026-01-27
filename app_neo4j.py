#!/usr/bin/env python
# app_neo4j.py - RAG Application với Neo4j Backend
"""
Multi-user Interactive RAG Application với Neo4j
=================================================

Ứng dụng RAG sử dụng Neo4j Graph Database với:
- Discovery Agent: Tìm kiếm người dùng toàn cục
- Personal RAG: Xem chi tiết claims của từng user
- ReBAC: Relationship-based Access Control
- Temporal Ranking: Time decay scoring

Usage:
    streamlit run app_neo4j.py
"""

import streamlit as st
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional

# Import Neo4j modules
from utils.neo4j_client import get_neo4j_client
from utils.embeddings import load_embedder
from utils.discovery_agent import DiscoveryAgent, UserCard, SearchResult
from utils.rebac import determine_access_scope, AccessTag
from utils.temporal_ranking import calculate_freshness_score, calculate_combined_score, ScoredClaim


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="RAG + Neo4j",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "viewer_id" not in st.session_state:
        st.session_state.viewer_id = None
    if "selected_user" not in st.session_state:
        st.session_state.selected_user = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = None
    if "neo4j_connected" not in st.session_state:
        st.session_state.neo4j_connected = False
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "current_claims" not in st.session_state:
        st.session_state.current_claims = []


# ============================================================================
# NEO4J CONNECTION
# ============================================================================

@st.cache_resource
def get_client():
    """Get Neo4j client singleton."""
    try:
        client = get_neo4j_client()
        return client
    except Exception as e:
        st.error(f"❌ Không thể kết nối Neo4j: {e}")
        return None


@st.cache_resource
def get_discovery_agent(_client):
    """Get Discovery Agent singleton."""
    return DiscoveryAgent(_client)


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar với user selection và search."""
    st.sidebar.title("🔐 Identity")
    
    # Get client
    client = get_client()
    if not client:
        st.sidebar.error("Neo4j chưa kết nối!")
        return
    
    # Load all users
    try:
        stats = client.get_database_stats()
        st.sidebar.success(f"✅ Neo4j: {stats['nodes'].get('User', 0)} Users, {stats['nodes'].get('Claim', 0)} Claims")
    except Exception as e:
        st.sidebar.error(f"Lỗi: {e}")
        return
    
    # Get user list
    users = get_all_users(client)
    user_options = {u["user_id"]: f"{u['name']} ({', '.join(u.get('roles', []))})" for u in users}
    
    # Viewer selection
    st.sidebar.markdown("### 👤 Bạn là ai?")
    viewer_id = st.sidebar.selectbox(
        "Chọn Viewer ID",
        options=["(Visitor)"] + list(user_options.keys()),
        format_func=lambda x: "👤 Visitor (Stranger)" if x == "(Visitor)" else f"👤 {user_options.get(x, x)}",
        key="viewer_select"
    )
    
    if viewer_id != "(Visitor)":
        st.session_state.viewer_id = viewer_id
        viewer = next((u for u in users if u["user_id"] == viewer_id), None)
        if viewer:
            st.sidebar.info(f"**Role:** {', '.join(viewer.get('roles', []))}\n\n**Reputation:** {viewer.get('reputation_score', 0):.2f}")
    else:
        st.session_state.viewer_id = None
    
    st.sidebar.markdown("---")
    
    # Discovery Agent Search
    st.sidebar.markdown("### 🔍 Discovery Agent")
    st.sidebar.caption("Tìm kiếm người dùng theo skill")
    
    search_query = st.sidebar.text_input(
        "Tìm kiếm",
        placeholder="VD: Python, React, RAG...",
        key="search_input"
    )
    
    if st.sidebar.button("🔎 Tìm kiếm", use_container_width=True):
        if search_query:
            agent = get_discovery_agent(client)
            results = agent.search_users(search_query, limit=10)
            st.session_state.search_results = results
            st.session_state.search_query = search_query  # Save query for semantic scoring
            st.session_state.selected_user = None
    
    # Quick skills
    st.sidebar.markdown("**Quick Search:**")
    cols = st.sidebar.columns(3)
    quick_skills = ["Python", "React", "RAG"]
    for i, skill in enumerate(quick_skills):
        if cols[i].button(skill, key=f"quick_{skill}"):
            agent = get_discovery_agent(client)
            results = agent.search_users(skill, limit=10)
            st.session_state.search_query = skill  # Save query
            st.session_state.search_results = results
            st.session_state.selected_user = None


@st.cache_data(ttl=60)
def get_all_users(_client) -> List[Dict]:
    """Get all users from Neo4j."""
    cypher = """
    MATCH (u:User)
    RETURN u.user_id AS user_id, 
           u.name AS name, 
           u.roles AS roles,
           u.reputation_score AS reputation_score,
           u.bio AS bio
    ORDER BY u.name
    """
    with _client.driver.session() as session:
        result = session.run(cypher)
        return [dict(record) for record in result]


# ============================================================================
# MAIN CONTENT
# ============================================================================

def render_main_content():
    """Render main content area."""
    client = get_client()
    if not client:
        st.warning("⚠️ Vui lòng đảm bảo Neo4j đang chạy!")
        st.code("docker-compose up -d", language="bash")
        return
    
    # Header
    st.title("🔍 RAG Application với Neo4j")
    
    viewer_id = st.session_state.viewer_id
    if viewer_id:
        st.caption(f"👤 Đang xem với tư cách: **{viewer_id}**")
    else:
        st.caption("👤 Đang xem với tư cách: **Visitor (Stranger)**")
    
    st.markdown("---")
    
    # Two columns layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        render_search_results()
    
    with col2:
        render_user_details(client)


def render_search_results():
    """Render search results from Discovery Agent."""
    st.subheader("📋 Kết quả tìm kiếm")
    
    results = st.session_state.search_results
    
    if not results:
        st.info("💡 Sử dụng sidebar để tìm kiếm người dùng theo skill")
        return
    
    st.caption(f"Tìm thấy **{results.total_users_found}** users trong {results.search_time_ms}ms")
    
    if results.entities_searched:
        st.caption(f"Skills: {', '.join(results.entities_searched)}")
    
    # Display user cards
    for card in results.user_cards:
        with st.container():
            # Card header
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{card.name}** (`{card.user_id}`)")
            with col2:
                st.metric("Relevance", f"{card.relevance_score:.0%}")
            
            # Card body
            st.caption(f"🏷️ {', '.join(card.roles)}")
            st.caption(f"📊 {card.public_claims_count} claims | ✅ {card.verified_claims_count} verified")
            
            if card.matched_skills:
                st.caption(f"🎯 Skills: {', '.join(card.matched_skills)}")
            
            # Select button
            if st.button(f"Xem chi tiết →", key=f"select_{card.user_id}"):
                st.session_state.selected_user = card.user_id
                st.rerun()
            
            st.markdown("---")


def render_user_details(client):
    """Render detailed view of selected user."""
    st.subheader("👤 Chi tiết User")
    
    selected_user = st.session_state.selected_user
    viewer_id = st.session_state.viewer_id
    
    if not selected_user:
        st.info("👈 Chọn một user từ kết quả tìm kiếm để xem chi tiết")
        return
    
    # Get user info
    user = get_user_by_id(client, selected_user)
    if not user:
        st.error(f"Không tìm thấy user: {selected_user}")
        return
    
    # User header
    st.markdown(f"### {user['name']}")
    st.caption(f"ID: `{user['user_id']}` | Roles: {', '.join(user.get('roles', []))}")
    
    if user.get('bio'):
        st.markdown(f"_{user['bio']}_")
    
    st.markdown("---")
    
    # Determine access scope
    access_scope = determine_access_scope(viewer_id, selected_user, client)
    
    # Display access info - AccessScope is an object with allowed_tags property
    access_tags = access_scope.allowed_tags
    st.info(f"🔐 **Access Scope:** {', '.join(access_tags)}")
    
    # Get claims with ReBAC
    claims = get_user_claims_with_access(client, selected_user, access_tags)
    
    # Save claims to session for chat
    st.session_state.current_claims = claims
    
    # Get search query for semantic scoring
    search_query = st.session_state.search_query
    
    # Create tabs for Claims view and Chat
    tab1, tab2 = st.tabs(["📋 Claims", "💬 Chat với RAG"])
    
    with tab1:
        # Rank by temporal decay + semantic (if query exists)
        if claims:
            scored_claims = score_claims_with_embeddings(claims, search_query)
            display_claims(scored_claims, access_tags)
        else:
            st.warning("Không có claims nào bạn có quyền xem.")
    
    with tab2:
        render_chat_interface(user, claims)


@st.cache_resource
def get_embedder():
    """Load sentence embedder."""
    return load_embedder()


def score_claims_with_embeddings(claims: List[Dict], query: Optional[str] = None) -> List[ScoredClaim]:
    """Score claims with semantic similarity if query exists."""
    scored = []
    
    # Calculate semantic scores if we have a query
    semantic_scores = []
    if query:
        embedder = get_embedder()
        # Get query embedding
        query_embedding = embedder.encode([query])[0]
        
        # Get document embeddings
        docs = [c.get('content_summary', '') for c in claims]
        if docs:
            doc_embeddings = embedder.encode(docs)
            
            # Calculate cosine similarities
            for doc_emb in doc_embeddings:
                sim = np.dot(query_embedding, doc_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-8
                )
                semantic_scores.append(float(sim))
        else:
            semantic_scores = [0.5] * len(claims)
    else:
        semantic_scores = [0.5] * len(claims)  # Neutral if no query
    
    for claim, sem_score in zip(claims, semantic_scores):
        conf_score = claim.get('confidence_score', 0.3)
        fresh_score = calculate_freshness_score(claim)
        final = calculate_combined_score(sem_score, conf_score, fresh_score)
        
        scored.append(ScoredClaim(
            claim=claim,
            semantic_score=sem_score,
            confidence_score=conf_score,
            freshness_score=fresh_score,
            final_score=final
        ))
    
    scored.sort(key=lambda x: x.final_score, reverse=True)
    return scored


@st.cache_data(ttl=30)
def get_user_by_id(_client, user_id: str) -> Optional[Dict]:
    """Get user by ID."""
    cypher = """
    MATCH (u:User {user_id: $user_id})
    RETURN u.user_id AS user_id,
           u.name AS name,
           u.bio AS bio,
           u.roles AS roles,
           u.reputation_score AS reputation_score
    """
    with _client.driver.session() as session:
        result = session.run(cypher, user_id=user_id)
        record = result.single()
        return dict(record) if record else None


def get_user_claims_with_access(client, user_id: str, access_tags: List[str]) -> List[Dict]:
    """Get claims that viewer has access to."""
    
    cypher = """
    MATCH (u:User {user_id: $user_id})-[:MAKES_CLAIM]->(c:Claim)
    WHERE any(tag IN c.access_tags WHERE tag IN $access_tags)
    OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
    OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(ev:Evidence)
    RETURN c.claim_id AS claim_id,
           c.topic AS topic,
           c.content_summary AS content_summary,
           c.status AS status,
           c.confidence_score AS confidence_score,
           c.access_tags AS access_tags,
           c.created_at AS created_at,
           c.updated_at AS updated_at,
           c.verified_by AS verified_by,
           collect(DISTINCT e.name) AS entities,
           collect(DISTINCT ev.url) AS evidence_urls
    ORDER BY c.updated_at DESC
    """
    
    with client.driver.session() as session:
        result = session.run(cypher, user_id=user_id, access_tags=access_tags)
        return [dict(record) for record in result]


def display_claims(scored_claims: List[ScoredClaim], access_tags: List[str]):
    """Display scored claims with details."""
    st.markdown(f"### 📋 Claims ({len(scored_claims)})")
    
    # Check if viewer can see sensitive info
    can_see_hr = "hr_sensitive" in access_tags
    
    for sc in scored_claims:
        claim = sc.claim
        
        # Determine card style based on status
        if claim.get("status") == "attested":
            icon = "✅"
        else:
            icon = "📝"
        
        with st.expander(f"{icon} {claim.get('topic', 'Unknown')} - Score: {sc.final_score:.2f}"):
            # Content
            st.markdown(f"**{claim.get('content_summary', '')}**")
            
            # Scores
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Final", f"{sc.final_score:.2f}")
            col2.metric("Confidence", f"{sc.confidence_score:.2f}")
            col3.metric("Freshness", f"{sc.freshness_score:.2f}")
            col4.metric("Semantic", f"{sc.semantic_score:.2f}")
            
            # Metadata
            st.caption(f"📅 Updated: {claim.get('updated_at', 'N/A')}")
            st.caption(f"🏷️ Status: {claim.get('status', 'N/A')}")
            st.caption(f"🔐 Access: {', '.join(claim.get('access_tags', []))}")
            
            # Entities
            entities = claim.get("entities", [])
            if entities:
                st.caption(f"🎯 Entities: {', '.join(entities)}")
            
            # Evidence
            evidence_urls = claim.get("evidence_urls", [])
            if evidence_urls and evidence_urls[0]:
                st.caption("📎 Evidence:")
                for url in evidence_urls:
                    if url:
                        st.markdown(f"  - [{url}]({url})")
            
            # Verified by
            if claim.get("verified_by"):
                st.success(f"✅ Verified by: {claim['verified_by']}")


# ============================================================================
# CHAT INTERFACE
# ============================================================================

def render_chat_interface(user: Dict, claims: List[Dict]):
    """Render chat interface for querying user's personal RAG."""
    st.markdown("### 💬 Hỏi đáp với RAG cá nhân")
    st.info(f"Đặt câu hỏi về **{user.get('name', 'Unknown')}** dựa trên claims của họ.")
    
    # Initialize chat for this user
    user_id = user.get("user_id", "unknown")
    chat_key = f"chat_{user_id}"
    
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    # Display chat history
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input(f"Hỏi về {user.get('name', 'người này')}..."):
        # Add user message
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response using RAG
        with st.chat_message("assistant"):
            with st.spinner("Đang tìm kiếm thông tin..."):
                response = generate_rag_response(prompt, claims, user)
                st.markdown(response)
        
        # Save assistant response
        st.session_state[chat_key].append({"role": "assistant", "content": response})
        st.rerun()
    
    # Clear chat button
    if st.session_state[chat_key]:
        if st.button("🗑️ Xóa lịch sử chat", key=f"clear_{user_id}"):
            st.session_state[chat_key] = []
            st.rerun()


def generate_rag_response(query: str, claims: List[Dict], user: Dict) -> str:
    """Generate response based on RAG over user's claims."""
    if not claims:
        return f"❌ Không có claims nào của {user.get('name', 'người này')} để tìm kiếm."
    
    # Get embedder and embed query
    embedder = get_embedder()
    query_embedding = embedder.encode([query])[0]
    
    # Score claims by semantic similarity
    claim_scores = []
    for claim in claims:
        content = claim.get("content_summary", "")
        if content:
            content_embedding = embedder.encode([content])[0]
            similarity = float(np.dot(query_embedding, content_embedding) / 
                             (np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding) + 1e-8))
            claim_scores.append((claim, similarity))
    
    # Sort by similarity
    claim_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Get top relevant claims
    top_k = 3
    relevant_claims = claim_scores[:top_k]
    
    if not relevant_claims or relevant_claims[0][1] < 0.2:
        return f"🤔 Không tìm thấy thông tin liên quan đến câu hỏi của bạn trong claims của {user.get('name', 'người này')}."
    
    # Build response
    response_parts = []
    response_parts.append(f"📋 **Tìm thấy {len(relevant_claims)} claims liên quan:**\n")
    
    for i, (claim, score) in enumerate(relevant_claims, 1):
        content = claim.get("content_summary", "N/A")
        confidence = claim.get("confidence", 0)
        entities = claim.get("entities", [])
        evidence = claim.get("evidence_urls", [])
        
        response_parts.append(f"**{i}. {content}**")
        response_parts.append(f"   - 📊 Độ tương đồng: {score:.2%}")
        response_parts.append(f"   - 🎯 Độ tin cậy: {confidence:.0%}")
        
        if entities:
            response_parts.append(f"   - 🏷️ Entities: {', '.join(entities)}")
        
        if evidence and evidence[0]:
            response_parts.append(f"   - 📎 Evidence: {evidence[0]}")
        
        response_parts.append("")
    
    # Summary
    user_name = user.get("name", "Người này")
    top_claim = relevant_claims[0][0].get("content_summary", "")
    response_parts.append(f"---\n💡 **Tóm tắt:** Dựa trên câu hỏi của bạn, thông tin liên quan nhất về {user_name} là: *\"{top_claim}\"*")
    
    return "\n".join(response_parts)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    init_session_state()
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
