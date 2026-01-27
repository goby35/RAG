#!/usr/bin/env python
# app_human_first.py - Human-First RAG Application
"""
Human-First RAG Application
============================

Ứng dụng RAG với nguyên tắc Human-First:
- Chat người-người là mặc định
- AI chỉ đại diện khi người dùng offline
- Lịch hẹn cần xác nhận từ người thật
- Vai trò được suy ra từ Graph, không chọn thủ công

Usage:
    streamlit run app_human_first.py --server.port 8503
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

# Import modules
from utils.neo4j_client import get_neo4j_client, Neo4jClient
from utils.auth import (
    AuthManager, PresenceStatus, UserSession,
    init_auth_session_state, get_current_session, is_logged_in, 
    get_current_user_id, get_current_user_name
)
from utils.presence import PresenceManager, PresenceInfo
from utils.chat_router import ChatRouter, MessageType, RouteType, Message
from utils.scheduler import PersonalScheduler, EventStatus, EventType
from utils.ai_agent import AIFallbackAgent
from utils.discovery_agent import DiscoveryAgent
from utils.rebac import determine_access_scope
from utils.embeddings import load_embedder


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Human-First RAG",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    init_auth_session_state()
    
    if "neo4j_client" not in st.session_state:
        st.session_state.neo4j_client = None
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = None
    if "current_chat_user" not in st.session_state:
        st.session_state.current_chat_user = None
    if "page" not in st.session_state:
        st.session_state.page = "home"


def get_client() -> Neo4jClient:
    """Get or create Neo4j client."""
    if st.session_state.neo4j_client is None:
        st.session_state.neo4j_client = get_neo4j_client()
    return st.session_state.neo4j_client


def get_auth_manager() -> AuthManager:
    """Get or create AuthManager."""
    if st.session_state.auth_manager is None:
        st.session_state.auth_manager = AuthManager(get_client())
    return st.session_state.auth_manager


# ============================================================================
# LOGIN PAGE
# ============================================================================

def render_login_page():
    """Render login page."""
    st.title("👤 Human-First RAG")
    st.markdown("### Đăng nhập để bắt đầu")
    
    auth = get_auth_manager()
    users = auth.get_available_users()
    
    if not users:
        st.warning("Không có người dùng nào trong hệ thống. Chạy seed_data.py để tạo dữ liệu mẫu.")
        return
    
    # User selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        user_options = {u.get("name", u.get("user_id")): u.get("user_id") for u in users}
        selected_name = st.selectbox(
            "Chọn người dùng",
            options=list(user_options.keys()),
            help="Trong demo, bạn có thể đăng nhập như bất kỳ người dùng nào"
        )
        selected_user_id = user_options[selected_name]
        
        # Show user info
        selected_user = next((u for u in users if u.get("user_id") == selected_user_id), None)
        if selected_user:
            st.info(f"**Bio**: {selected_user.get('bio', 'Chưa có thông tin')}")
    
    with col2:
        st.markdown("### ")  # Spacer
        if st.button("🔑 Đăng nhập", type="primary", use_container_width=True):
            session = auth.login(selected_user_id)
            if session:
                st.session_state.auth_session = session
                st.success(f"Đăng nhập thành công: {session.user_name}")
                st.rerun()
            else:
                st.error("Đăng nhập thất bại")
    
    # Info box
    st.markdown("---")
    st.markdown("""
    ### ℹ️ Human-First RAG là gì?
    
    **Nguyên tắc cốt lõi:**
    - 👥 **Chat người-người** là mặc định, không phải AI
    - 🤖 **AI chỉ đại diện** khi người dùng offline
    - 📅 **Lịch hẹn** cần xác nhận từ người thật
    - 🔐 **Vai trò** tự động suy ra từ quan hệ (không chọn thủ công)
    """)


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar with navigation and status."""
    session = get_current_session()
    
    with st.sidebar:
        st.markdown("## 👤 Human-First RAG")
        st.markdown("---")
        
        if session:
            # User info
            st.markdown(f"### 👋 Xin chào, {session.user_name}")
            
            # Presence status
            status_emoji = {
                PresenceStatus.ONLINE: "🟢",
                PresenceStatus.AWAY: "🟡",
                PresenceStatus.BUSY: "🔴",
                PresenceStatus.OFFLINE: "⚫"
            }.get(session.presence_status, "⚫")
            
            st.markdown(f"**Trạng thái**: {status_emoji} {session.presence_status.value.title()}")
            
            # Status selector
            new_status = st.selectbox(
                "Thay đổi trạng thái",
                options=[PresenceStatus.ONLINE, PresenceStatus.AWAY, PresenceStatus.BUSY],
                format_func=lambda x: f"{status_emoji} {x.value.title()}",
                index=0 if session.presence_status == PresenceStatus.ONLINE else 1
            )
            
            if new_status != session.presence_status:
                auth = get_auth_manager()
                session = auth.set_presence(session, new_status)
                st.session_state.auth_session = session
                st.rerun()
            
            st.markdown("---")
            
            # Navigation
            st.markdown("### 📍 Điều hướng")
            
            if st.button("🏠 Trang chủ", use_container_width=True):
                st.session_state.page = "home"
                st.rerun()
            
            if st.button("💬 Tin nhắn", use_container_width=True):
                st.session_state.page = "messages"
                st.rerun()
            
            if st.button("📅 Lịch hẹn", use_container_width=True):
                st.session_state.page = "calendar"
                st.rerun()
            
            if st.button("🔍 Tìm kiếm", use_container_width=True):
                st.session_state.page = "search"
                st.rerun()
            
            if st.button("📋 Hồ sơ của tôi", use_container_width=True):
                st.session_state.page = "profile"
                st.rerun()
            
            st.markdown("---")
            
            # Unread messages
            router = ChatRouter(get_client())
            unread = router.get_unread_count(session.user_id)
            if unread > 0:
                st.warning(f"📬 Bạn có **{unread}** tin nhắn chưa đọc")
            
            # Pending events
            scheduler = PersonalScheduler(get_client())
            pending = scheduler.get_pending_confirmations(session.user_id)
            if pending:
                st.info(f"📅 Bạn có **{len(pending)}** lịch hẹn cần xác nhận")
            
            st.markdown("---")
            
            # Logout
            if st.button("🚪 Đăng xuất", use_container_width=True):
                auth = get_auth_manager()
                auth.logout(session)
                st.session_state.auth_session = None
                st.session_state.page = "home"
                st.rerun()


# ============================================================================
# HOME PAGE
# ============================================================================

def render_home_page():
    """Render home page with overview."""
    session = get_current_session()
    client = get_client()
    
    st.title(f"👋 Xin chào, {session.user_name}!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 💬 Tin nhắn")
        router = ChatRouter(client)
        unread = router.get_unread_count(session.user_id)
        st.metric("Chưa đọc", unread)
        
        if st.button("Xem tin nhắn →", key="goto_messages"):
            st.session_state.page = "messages"
            st.rerun()
    
    with col2:
        st.markdown("### 📅 Lịch hẹn")
        scheduler = PersonalScheduler(client)
        upcoming = scheduler.get_upcoming_events(session.user_id, days=7)
        st.metric("Tuần này", len(upcoming))
        
        if st.button("Xem lịch →", key="goto_calendar"):
            st.session_state.page = "calendar"
            st.rerun()
    
    with col3:
        st.markdown("### 👥 Kết nối")
        auth = get_auth_manager()
        relationships = auth.get_user_relationships(session.user_id)
        total_connections = sum(len(v) for v in relationships.values())
        st.metric("Kết nối", total_connections)
    
    st.markdown("---")
    
    # Online users
    st.markdown("### 🟢 Người dùng đang online")
    
    presence_mgr = PresenceManager(client)
    all_users = presence_mgr.get_all_users_presence()
    
    # Filter out current user
    other_users = [u for u in all_users if u.user_id != session.user_id]
    
    if not other_users:
        st.info("Không có người dùng khác trong hệ thống")
    else:
        # Deduplicate users by user_id
        seen_ids = set()
        unique_users = []
        for u in other_users:
            if u.user_id not in seen_ids:
                seen_ids.add(u.user_id)
                unique_users.append(u)
        
        cols = st.columns(min(len(unique_users), 4))
        for i, user in enumerate(unique_users[:4]):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{user.status_emoji} {user.user_name}**")
                    st.caption(user.status_text)
                    
                    if st.button("💬 Chat", key=f"home_chat_{user.user_id}_{i}"):
                        st.session_state.current_chat_user = user.user_id
                        st.session_state.page = "chat"
                        st.rerun()


# ============================================================================
# MESSAGES PAGE
# ============================================================================

def render_messages_page():
    """Render messages/inbox page."""
    session = get_current_session()
    client = get_client()
    router = ChatRouter(client)
    
    st.title("💬 Tin nhắn")
    
    # Get recent contacts
    contacts = router.get_recent_contacts(session.user_id)
    presence_mgr = PresenceManager(client)
    
    # Also add all users for new conversations
    all_users = client.get_all_users()
    all_user_ids = {c["user_id"] for c in contacts}
    
    for user in all_users:
        if user.get("user_id") not in all_user_ids and user.get("user_id") != session.user_id:
            contacts.append({
                "user_id": user.get("user_id"),
                "name": user.get("name"),
                "presence_status": "offline",
                "last_message_time": None
            })
    
    if not contacts:
        st.info("Chưa có cuộc trò chuyện nào")
        return
    
    # Contact list
    st.markdown("### 📋 Liên hệ")
    
    # Deduplicate contacts by user_id
    seen_contact_ids = set()
    unique_contacts = []
    for c in contacts:
        if c["user_id"] not in seen_contact_ids:
            seen_contact_ids.add(c["user_id"])
            unique_contacts.append(c)
    
    for idx, contact in enumerate(unique_contacts):
        user_id = contact["user_id"]
        name = contact["name"]
        
        # Get presence
        presence = presence_mgr.get_user_presence(user_id)
        status_emoji = presence.status_emoji if presence else "⚫"
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{status_emoji} {name}**")
            if contact.get("last_message_time"):
                st.caption(f"Tin nhắn gần nhất: {contact['last_message_time']}")
        
        with col2:
            if st.button("💬 Chat", key=f"open_chat_{user_id}_{idx}"):
                st.session_state.current_chat_user = user_id
                st.session_state.page = "chat"
                st.rerun()


# ============================================================================
# CHAT PAGE
# ============================================================================

def render_chat_page():
    """Render chat conversation page."""
    session = get_current_session()
    client = get_client()
    
    target_user_id = st.session_state.get("current_chat_user")
    if not target_user_id:
        st.warning("Chọn người để chat từ trang Tin nhắn")
        if st.button("← Quay lại"):
            st.session_state.page = "messages"
            st.rerun()
        return
    
    # Get target user info
    target_user = client.get_user(target_user_id)
    if not target_user:
        st.error("Người dùng không tồn tại")
        return
    
    target_name = target_user.get("name", target_user_id)
    
    # Get presence
    presence_mgr = PresenceManager(client)
    target_presence = presence_mgr.get_user_presence(target_user_id)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        status_emoji = target_presence.status_emoji if target_presence else "⚫"
        st.title(f"{status_emoji} Chat với {target_name}")
        
        # Show routing info
        routing = presence_mgr.get_routing_decision(target_user_id)
        if routing["ai_fallback"]:
            st.warning(f"⚠️ {target_name} đang offline. AI sẽ trả lời thay.")
        elif routing["route_to"] == "human_with_notification":
            st.info(f"ℹ️ {target_name} đang {target_presence.status_text.lower()}. Tin nhắn sẽ được lưu.")
    
    with col2:
        if st.button("← Quay lại"):
            st.session_state.page = "messages"
            st.rerun()
    
    st.markdown("---")
    
    # Chat history
    router = ChatRouter(client)
    messages = router.get_conversation(session.user_id, target_user_id)
    
    # Mark as read
    router.mark_conversation_as_read(session.user_id, target_user_id)
    
    # Display messages
    chat_container = st.container(height=400)
    with chat_container:
        for msg in messages:
            is_mine = msg.sender_id == session.user_id
            
            with st.chat_message("user" if is_mine else "assistant"):
                if msg.is_ai_response:
                    st.markdown(f"🤖 *AI đại diện {target_name}*")
                
                st.markdown(msg.content)
                st.caption(msg.timestamp.strftime("%H:%M %d/%m"))
                
                if msg.ai_disclaimer:
                    st.caption(f"_{msg.ai_disclaimer}_")
    
    # Send message
    if prompt := st.chat_input(f"Nhắn tin cho {target_name}..."):
        # Route message
        result = router.route_message(
            sender_id=session.user_id,
            receiver_id=target_user_id,
            content=prompt
        )
        
        # Save message
        router.save_message(result.message)
        
        # If AI fallback needed
        if result.ai_should_respond:
            ai_agent = AIFallbackAgent(client)
            ai_response = ai_agent.generate_response(
                query=prompt,
                target_user_id=target_user_id,
                requester_id=session.user_id
            )
            
            # Save AI response
            ai_msg = router.save_ai_response(result.message, ai_response.content)
        
        st.rerun()


# ============================================================================
# CALENDAR PAGE
# ============================================================================

def render_calendar_page():
    """Render calendar/scheduling page."""
    session = get_current_session()
    client = get_client()
    scheduler = PersonalScheduler(client)
    
    st.title("📅 Lịch hẹn")
    
    tab1, tab2, tab3 = st.tabs(["📋 Sắp tới", "⏳ Cần xác nhận", "➕ Tạo mới"])
    
    with tab1:
        st.markdown("### Lịch hẹn sắp tới (7 ngày)")
        
        upcoming = scheduler.get_upcoming_events(session.user_id, days=7)
        
        if not upcoming:
            st.info("Không có lịch hẹn nào trong 7 ngày tới")
        else:
            for event in upcoming:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        status_emoji = {
                            EventStatus.CONFIRMED: "✅",
                            EventStatus.PROPOSED: "📝",
                            EventStatus.PENDING_CONFIRMATION: "⏳"
                        }.get(event.status, "📅")
                        
                        st.markdown(f"**{status_emoji} {event.title}**")
                        st.caption(f"📅 {event.start_time.strftime('%H:%M %d/%m/%Y')}")
                        st.caption(f"⏱️ {event.duration_minutes} phút")
                    
                    with col2:
                        # Get other party name
                        other_id = event.invitee_id if event.proposer_id == session.user_id else event.proposer_id
                        other_user = client.get_user(other_id)
                        other_name = other_user.get("name", other_id) if other_user else other_id
                        st.markdown(f"👤 {other_name}")
                    
                    with col3:
                        if event.status == EventStatus.CONFIRMED:
                            if st.button("❌ Hủy", key=f"cancel_{event.event_id}"):
                                scheduler.cancel_event(event.event_id, session.user_id)
                                st.rerun()
    
    with tab2:
        st.markdown("### Lịch hẹn cần xác nhận")
        
        pending = scheduler.get_pending_confirmations(session.user_id)
        
        if not pending:
            st.success("Không có lịch hẹn nào cần xác nhận")
        else:
            for event in pending:
                with st.container(border=True):
                    proposer = client.get_user(event.proposer_id)
                    proposer_name = proposer.get("name", event.proposer_id) if proposer else event.proposer_id
                    
                    st.markdown(f"**📝 {event.title}**")
                    st.caption(f"Đề xuất bởi: {proposer_name}")
                    st.caption(f"📅 {event.start_time.strftime('%H:%M %d/%m/%Y')}")
                    
                    if event.is_ai_proposed:
                        st.warning("🤖 Lịch này được đề xuất bởi AI khi bạn offline")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Xác nhận", key=f"confirm_{event.event_id}"):
                            scheduler.confirm_event(event.event_id, session.user_id)
                            st.success("Đã xác nhận lịch hẹn!")
                            st.rerun()
                    with col2:
                        if st.button("❌ Từ chối", key=f"reject_{event.event_id}"):
                            scheduler.cancel_event(event.event_id, session.user_id, "Từ chối")
                            st.rerun()
    
    with tab3:
        st.markdown("### Tạo lịch hẹn mới")
        
        # Get users to invite
        all_users = client.get_all_users()
        other_users = [u for u in all_users if u.get("user_id") != session.user_id]
        
        if not other_users:
            st.info("Không có người dùng khác để mời")
        else:
            user_options = {u.get("name"): u.get("user_id") for u in other_users}
            
            invitee_name = st.selectbox("Mời", options=list(user_options.keys()))
            invitee_id = user_options[invitee_name]
            
            title = st.text_input("Tiêu đề", value="Meeting")
            
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Ngày", value=datetime.now() + timedelta(days=1))
            with col2:
                time = st.time_input("Giờ", value=datetime.now().replace(hour=10, minute=0))
            
            duration = st.slider("Thời lượng (phút)", 15, 120, 30)
            
            if st.button("📅 Tạo lịch hẹn", type="primary"):
                start_time = datetime.combine(date, time)
                end_time = start_time + timedelta(minutes=duration)
                
                event = scheduler.propose_event(
                    proposer_id=session.user_id,
                    invitee_id=invitee_id,
                    title=title,
                    start_time=start_time,
                    end_time=end_time
                )
                
                st.success(f"Đã gửi lời mời đến {invitee_name}!")


# ============================================================================
# SEARCH PAGE
# ============================================================================

def render_search_page():
    """Render user search page using Discovery Agent."""
    session = get_current_session()
    client = get_client()
    
    st.title("🔍 Tìm kiếm người dùng")
    
    # Search input
    query = st.text_input("Tìm theo kỹ năng, công nghệ...", placeholder="Python, React, RAG...")
    
    if query:
        agent = DiscoveryAgent(client)
        results = agent.search_users(query)
        
        if not results.users:
            st.info(f"Không tìm thấy người dùng nào liên quan đến '{query}'")
        else:
            st.success(f"Tìm thấy {len(results.users)} người dùng")
            
            for idx, user_card in enumerate(results.users):
                with st.container(border=True):
                    # Get presence
                    presence_mgr = PresenceManager(client)
                    presence = presence_mgr.get_user_presence(user_card.user_id)
                    status_emoji = presence.status_emoji if presence else "⚫"
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"### {status_emoji} {user_card.name}")
                        st.markdown(f"🏷️ **Skills**: {', '.join(user_card.skills)}")
                        st.caption(f"📋 {user_card.claim_count} claims")
                        
                        # Show relationship
                        auth = get_auth_manager()
                        relationship = auth.infer_relationship(session.user_id, user_card.user_id)
                        if relationship != "STRANGER":
                            st.caption(f"🤝 {relationship}")
                    
                    with col2:
                        if st.button("💬 Chat", key=f"search_chat_{user_card.user_id}_{idx}"):
                            st.session_state.current_chat_user = user_card.user_id
                            st.session_state.page = "chat"
                            st.rerun()
                        
                        if st.button("📋 Xem hồ sơ", key=f"search_profile_{user_card.user_id}_{idx}"):
                            st.session_state.viewing_profile = user_card.user_id
                            st.session_state.page = "view_profile"
                            st.rerun()


# ============================================================================
# PROFILE PAGE
# ============================================================================

def render_profile_page():
    """Render current user's profile."""
    session = get_current_session()
    client = get_client()
    
    st.title("📋 Hồ sơ của tôi")
    
    user = client.get_user(session.user_id)
    if not user:
        st.error("Không tìm thấy thông tin người dùng")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### 👤 {user.get('name')}")
        st.markdown(f"**Bio**: {user.get('bio', 'Chưa có thông tin')}")
        
        # Get claims
        claims = client.get_claims_by_user(session.user_id)
        
        st.markdown("### 📋 Claims của tôi")
        
        if not claims:
            st.info("Bạn chưa có claim nào")
        else:
            for claim in claims:
                with st.expander(f"📄 {claim.get('content_summary', '')[:50]}..."):
                    st.markdown(f"**{claim.get('content_summary')}**")
                    st.caption(f"Status: {claim.get('status')} | Confidence: {claim.get('confidence_score', 0):.0%}")
                    st.caption(f"Access: {claim.get('access_level', 'public')}")
    
    with col2:
        st.markdown("### 🤝 Kết nối")
        
        auth = get_auth_manager()
        relationships = auth.get_user_relationships(session.user_id)
        
        for rel_type, users in relationships.items():
            if users:
                st.markdown(f"**{rel_type}**: {len(users)}")
                for u in users:
                    st.caption(f"• {u['name']}")


# ============================================================================
# VIEW OTHER PROFILE PAGE
# ============================================================================

def render_view_profile_page():
    """Render another user's profile."""
    session = get_current_session()
    client = get_client()
    
    target_user_id = st.session_state.get("viewing_profile")
    if not target_user_id:
        st.warning("Chọn người dùng để xem hồ sơ")
        return
    
    target_user = client.get_user(target_user_id)
    if not target_user:
        st.error("Người dùng không tồn tại")
        return
    
    target_name = target_user.get("name", target_user_id)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        presence_mgr = PresenceManager(client)
        presence = presence_mgr.get_user_presence(target_user_id)
        status_emoji = presence.status_emoji if presence else "⚫"
        
        st.title(f"{status_emoji} {target_name}")
        st.markdown(f"**Bio**: {target_user.get('bio', 'Chưa có thông tin')}")
    
    with col2:
        if st.button("← Quay lại"):
            st.session_state.page = "search"
            st.rerun()
        
        if st.button("💬 Chat"):
            st.session_state.current_chat_user = target_user_id
            st.session_state.page = "chat"
            st.rerun()
    
    st.markdown("---")
    
    # Determine access
    auth = get_auth_manager()
    relationship = auth.infer_relationship(session.user_id, target_user_id)
    access_scope = determine_access_scope(client, session.user_id, target_user_id)
    
    st.info(f"🤝 Quan hệ: **{relationship}** | Quyền truy cập: {', '.join(access_scope.allowed_tags)}")
    
    # Get accessible claims
    allowed_tags = access_scope.allowed_tags
    
    query = """
    MATCH (u:User {user_id: $user_id})-[:MAKES_CLAIM]->(c:Claim)
    WHERE c.access_level IN $allowed_tags
    OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
    RETURN c, collect(DISTINCT e.name) as entities
    ORDER BY c.confidence_score DESC
    """
    
    result = client.run_query(query, {
        "user_id": target_user_id,
        "allowed_tags": allowed_tags
    })
    
    if not result:
        st.info("Không có thông tin nào được chia sẻ với bạn")
    else:
        st.markdown("### 📋 Thông tin được chia sẻ")
        
        for row in result:
            claim = row["c"]
            entities = row.get("entities", [])
            
            with st.container(border=True):
                st.markdown(f"**{claim.get('content_summary')}**")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Confidence", f"{claim.get('confidence_score', 0):.0%}")
                col2.caption(f"Status: {claim.get('status')}")
                col3.caption(f"Access: {claim.get('access_level')}")
                
                if entities:
                    st.caption(f"🏷️ {', '.join(entities)}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    init_session_state()
    
    # Check connection
    try:
        client = get_client()
    except Exception as e:
        st.error(f"Không thể kết nối Neo4j: {e}")
        st.info("Chạy `docker-compose up -d` để khởi động Neo4j")
        return
    
    # Check login
    if not is_logged_in():
        render_login_page()
        return
    
    # Render sidebar
    render_sidebar()
    
    # Render main content based on page
    page = st.session_state.get("page", "home")
    
    if page == "home":
        render_home_page()
    elif page == "messages":
        render_messages_page()
    elif page == "chat":
        render_chat_page()
    elif page == "calendar":
        render_calendar_page()
    elif page == "search":
        render_search_page()
    elif page == "profile":
        render_profile_page()
    elif page == "view_profile":
        render_view_profile_page()
    else:
        render_home_page()


if __name__ == "__main__":
    main()
