# CHAT_SYSTEM_CONTEXT.md (Chat & History Intelligence)

## 1. Domain Overview
This module handles the core AI conversational capabilities, including thread management (history sidebar), message persistence, and auto-titling. It integrates directly with the existing authentication system (Session-based).

## 2. Database Schema (PostgreSQL via Django ORM)

We use two primary models to separate the "Sidebar History" from the "Actual Chat Content" for performance reasons.

### 2.1 `Conversation` Model (The Thread)
Represents a single chat session. Displayed in the "All History" sidebar.
- `id`: UUID (Primary Key).
- `user`: ForeignKey to `User` model (Indexed).
- `title`: String (Max 100 chars). Default: "New Chat". Updated asynchronously.
- `created_at`: DateTime (auto_now_add).
- `updated_at`: DateTime (auto_now). Used to sort the sidebar (latest active chats first).

### 2.2 `Message` Model (The Content)
Represents individual messages within a Conversation.
- `id`: UUID (Primary Key).
- `conversation`: ForeignKey to `Conversation` (Indexed, `on_delete=CASCADE`).
- `role`: CharField (Choices: `user`, `assistant`, `system`).
- `content`: TextField (The actual text).
- `created_at`: DateTime (auto_now_add). Used for sorting messages chronologically.

## 3. Architecture & Performance

### 3.1 Pagination Strategy
- **Conversations List (Sidebar)**: Standard DRF `PageNumberPagination` or `CursorPagination` (e.g., 20 items per page).
- **Messages List (Chat Window)**: `CursorPagination` is highly recommended for infinite scrolling (loading older messages as the user scrolls up).

### 3.2 Auto-Titling (Background Task)
Generating titles synchronously slows down the user's chat response.
- **Trigger**: Fired after the *first* AI response in a new conversation.
- **Execution**: Should be handed off to a background worker (e.g., Celery or Django-Q) to call a lightweight LLM prompt: *"Summarize this in 3-5 words"*.
- **Updates**: Once the background task generates the title, it updates the `Conversation.title`. The frontend can pick this up via a subsequent `GET` or WebSocket/SSE event.

### 3.3 Security & Authorization
- **Object-Level Permissions**: Every DRF View/ViewSet MUST ensure `request.user == conversation.user`. A user cannot fetch or append messages to another user's `conversation_id`.
- **Authentication**: Requires the standard Session Cookie (`IsAuthenticated` permission). CSRF token required for POST/PATCH/DELETE.


