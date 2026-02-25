# Navid API Contract v1 (Chat & History)

Audience: Shahdad, Alireza
Scope: Endpoints for managing chat threads (history) and sending/receiving messages.
Prerequisite: All endpoints require a valid Session Cookie and CSRF Token (for state-changing methods).

---

## 1) Base URL

All chat-related endpoints are prefixed with:

`/api/v1/chat`

---

## 2) Conversation (History) Endpoints

These endpoints power the sidebar ("All History").

### 2.1 List Conversations (Sidebar)
`GET /api/v1/chat/conversations`

**Frontend sends:**
- Query Params (optional): `?page=1&size=20`

**Backend returns `200`:** (Ordered by `updated_at` descending)
```json
{
  "count": 45,
  "next": "/api/v1/chat/conversations?page=2",
  "previous": null,
  "results": [
    {
      "id": "conv_8f7e6d",
      "title": "React Component Refactor",
      "createdAt": "2026-02-16T14:30:00.000Z",
      "updatedAt": "2026-02-16T15:45:00.000Z"
    },
    {
      "id": "conv_1a2b3c",
      "title": "New Chat",
      "createdAt": "2026-02-15T09:12:00.000Z",
      "updatedAt": "2026-02-15T09:12:00.000Z"
    }
  ]
}
```
Errors: 401 UNAUTHORIZED

### 2.2 Create New Conversation
`POST /api/v1/chat/conversations`

**Frontend sends:** Empty body `{}`

**Backend returns 201:**
```json
{
  "id": "conv_9x8y7z",
  "title": "New Chat",
  "createdAt": "2026-02-16T16:00:00.000Z",
  "updatedAt": "2026-02-16T16:00:00.000Z"
}
```

### 2.3 Update Conversation Title (Rename)
`PATCH /api/v1/chat/conversations/{conversationId}`

**Frontend sends:**
```json
{
  "title": "My Custom Title"
}
```

**Backend returns 200:**
```json
{
  "id": "conv_9x8y7z",
  "title": "My Custom Title",
  "updatedAt": "2026-02-16T16:05:00.000Z"
}
```
Errors: 403 FORBIDDEN (Not the owner), 404 NOT_FOUND

### 2.4 Delete Conversation
`DELETE /api/v1/chat/conversations/{conversationId}`

**Backend returns:** 204 No Content (Cascade deletes all related messages)

---

## 3) Message Endpoints
These endpoints power the main chat window.

### 3.1 List Messages for a Conversation
`GET /api/v1/chat/conversations/{conversationId}/messages`

**Frontend sends:** Query Params: `?cursor=...` (For scrolling up).

**Backend returns 200:** (Ordered by `created_at` ascending)
```json
{
  "nextCursor": null,
  "previousCursor": "cD0yMDI2LTAyLTE2VDE0OjMwOjAw",
  "results": [
    {
      "id": "msg_111",
      "role": "user",
      "content": "How do I center a div?",
      "createdAt": "2026-02-16T14:30:00.000Z"
    },
    {
      "id": "msg_112",
      "role": "assistant",
      "content": "You can use flexbox...",
      "createdAt": "2026-02-16T14:30:05.000Z"
    }
  ]
}
```
Errors: 403 FORBIDDEN, 404 NOT_FOUND

### 3.2 Send a Message (Logic & Context Management)
`POST /api/v1/chat/conversations/{conversationId}/messages`

**Frontend sends:**
The frontend is DUMB regarding history. It ONLY sends the new message.
```json
{
  "content": "Can you convert that to React?"
}
```

**Backend Internal Behavior (Strict Requirements):**
1.  **Context Assembly (Memory):** Backend queries the DB for the last ~10 messages of this conversationId, appends the new user message, and sends the entire array to the LLM.
2.  **Persistence:** Save both the User message and AI response to the DB. Update `Conversation.updated_at`.
3.  **Auto-Titling (Background Job):** If this is the first interaction (total msg count = 2), do not block the main thread. Dispatch a background worker (e.g., Celery) to use a cheaper LLM to generate a 3-5 word title and update `Conversation.title`.

**Backend returns 200:**
```json
{
  "id": "msg_114",
  "role": "assistant",
  "content": "Sure, here is the React version...",
  "createdAt": "2026-02-16T14:32:00.000Z"
}
```
(Frontend Note: On receiving 200 OK for the FIRST message of a new chat, quietly call `GET /conversations` in the background to refresh the sidebar, as the backend will have auto-generated the title by then).

Errors: 400 VALIDATION_ERROR, 403 FORBIDDEN, 404 NOT_FOUND, 429 RATE_LIMITED, 503 SERVICE_UNAVAILABLE
---
### 3.3 Rate AI Message (Feedback)
`PATCH /api/v1/chat/messages/{messageId}/feedback`

**Rule:** Users MUST rate the previous `assistant` message (Good/Bad) before they are allowed to send a new message in the same conversation.

**Frontend sends:**
```json
{
  "feedback": "good" // Enum: "good", "bad"
}
Backend returns 200:
Returns the updated Message object.
code
JSON
{
  "id": "msg_123e4567",
  "role": "assistant",
  "content": "Sure, here is the React version...",
  "createdAt": "2026-02-16T14:32:00.000Z",
  "feedback": "good"
}
Errors:
400 VALIDATION_ERROR (Invalid feedback value)
403 FORBIDDEN (Trying to rate someone else's message)
404 NOT_FOUND (Message does not exist)
---

## 4) Streaming AI Responses (Optional but Recommended)
If the frontend requires a typing effect (like ChatGPT), use Server-Sent Events (SSE).

`POST /api/v1/chat/conversations/{conversationId}/messages/stream`

**Frontend Headers:** `Accept: text/event-stream`

**Backend returns 200 OK (Chunked transfer encoding):**
```text
data: {"chunk": "Sure!"}
data: {"chunk": " Here is the"}
data: {"chunk": " React code."}
data: {"status": "done", "fullMessageId": "msg_114"}
```

---

### Important Notes for Your Development Team

1.  **Database Separation (Normalization)**: Notice that we separated `Conversation` (thread headers) from `Messages` (chat content). This is the exact architectural decision that allows the sidebar (with potentially hundreds of chats) to load in milliseconds when the user logs in, because the heavy text payloads of the actual messages are excluded from the initial query.
2.  **Security (Ownership Validation)**: For all message-related endpoints (Section 3), the backend MUST verify that the requesting user (`request.user.id`) is the explicit owner of the requested `conversationId`. Failing to validate this tenant isolation must result in a `403 FORBIDDEN` error.
3.  **Streaming (Typing Effect)**: As outlined in Section 4, if you want your AI bot to stream its response word-by-word (simulating a typing effect like ChatGPT), you must implement Server-Sent Events (SSE) using the `text/event-stream` response type instead of a standard blocking JSON response.
