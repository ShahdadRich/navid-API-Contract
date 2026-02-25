# CHAT_SYSTEM_CONTEXT.md (Chat & History Intelligence)

## 1. Domain Overview
This module handles the core AI conversational capabilities, including thread management (history sidebar), message persistence, **context window management**, and auto-titling. It integrates directly with the existing authentication system (Session-based).

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

### 3.2 Context Management (The Memory Problem)
LLMs (OpenAI, Gemini, etc.) are inherently stateless. To allow the AI to remember the conversation:
- **Client-Side**: The frontend is "dumb". It ONLY sends the newly typed message.
- **Server-Side Assembly**: Before calling the AI provider, the backend must query the `Message` table, fetch the last $N$ messages (e.g., last 10 messages to save token costs), append the new user message, and send the entire array to the AI.

### 3.3 Auto-Titling (Background Task)
Generating titles synchronously blocks the main thread and slows down the user's chat response.
- **Trigger**: Fired ONLY after the *first* AI response in a new conversation (when message count is exactly 2).
- **Execution**: Must be handed off to a background worker (e.g., Celery or Django-Q).
- **Model Efficiency**: The background worker should use a faster, cheaper LLM (e.g., GPT-3.5-Turbo or Gemini-Flash) with a prompt like: *"Summarize this in 3-5 words"*.
- **Updates**: Once generated, it updates `Conversation.title`.

### 3.4 Security & Authorization
- **Object-Level Permissions**: Every DRF View/ViewSet MUST ensure `request.user == conversation.user`.
- **Authentication**: Requires the standard Session Cookie (`IsAuthenticated` permission). CSRF token required for POST/PATCH/DELETE.
