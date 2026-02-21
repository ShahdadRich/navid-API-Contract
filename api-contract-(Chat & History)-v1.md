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

## 2.1 List Conversations (Sidebar)

`GET /api/v1/chat/conversations`

### Frontend sends
- Query Params (optional): `?page=1&size=20`

### Backend returns `200`
Ordered by `updated_at` descending (newest active chats first).

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

### Errors
- `401 UNAUTHORIZED`

## 2.2 Create New Conversation

`POST /api/v1/chat/conversations`

### Frontend sends
- Empty body `{}` (or optional initial system prompt/settings).

### Backend returns `201`
```json
{
  "id": "conv_9x8y7z",
  "title": "New Chat",
  "createdAt": "2026-02-16T16:00:00.000Z",
  "updatedAt": "2026-02-16T16:00:00.000Z"
}
```

## 2.3 Update Conversation Title (Rename)

`PATCH /api/v1/chat/conversations/{conversationId}`

### Frontend sends
```json
{
  "title": "My Custom Title"
}
```

### Backend returns `200`
```json
{
  "id": "conv_9x8y7z",
  "title": "My Custom Title",
  "updatedAt": "2026-02-16T16:05:00.000Z"
}
```

### Errors
- `403 FORBIDDEN` (Not the owner)
- `404 NOT_FOUND`

## 2.4 Delete Conversation

`DELETE /api/v1/chat/conversations/{conversationId}`

### Backend returns
- `204 No Content` (Cascade deletes all related messages)

---

## 3) Message Endpoints

These endpoints power the main chat window.

## 3.1 List Messages for a Conversation

`GET /api/v1/chat/conversations/{conversationId}/messages`

### Frontend sends
- Query Params: `?cursor=...` (For loading older messages when scrolling up).

### Backend returns `200`
Ordered by `created_at` ascending (oldest to newest for proper chat UI display).

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
      "content": "You can use flexbox: `display: flex; justify-content: center; align-items: center;`",
      "createdAt": "2026-02-16T14:30:05.000Z"
    }
  ]
}
```

### Errors
- `403 FORBIDDEN` (Trying to view someone else's chat)
- `404 NOT_FOUND`

## 3.2 Send a Message (Standard JSON / Non-Streaming)

*Note: For modern AI apps, Server-Sent Events (SSE) streaming is preferred. This is the standard blocking fallback.*

`POST /api/v1/chat/conversations/{conversationId}/messages`

### Frontend sends
```json
{
  "content": "Can you give me an example in Tailwind?"
}
```

### Backend behavior
1. Saves the User's message to the database.
2. Sends the conversation history to the AI Model (OpenAI/Gemini/Local LLM).
3. Receives AI response.
4. Saves the AI's message to the database.
5. Updates `Conversation.updated_at`.
6. (Async) If this is the first interaction, triggers the Auto-Titling job.

### Backend returns `200`
Returns the AI's generated message.

```json
{
  "id": "msg_114",
  "role": "assistant",
  "content": "Sure! In Tailwind, you can use `flex justify-center items-center`.",
  "createdAt": "2026-02-16T14:32:00.000Z"
}
```

### Errors
- `400 VALIDATION_ERROR` (Empty message)
- `403 FORBIDDEN`
- `404 NOT_FOUND`
- `429 RATE_LIMITED` (Prevent API abuse)
- `503 SERVICE_UNAVAILABLE` (AI Provider is down)

---

## 4) Streaming AI Responses (Optional but Recommended)

If the frontend requires a typing effect (like ChatGPT), use Server-Sent Events (SSE).

`POST /api/v1/chat/conversations/{conversationId}/messages/stream`

### Frontend Headers
- `Accept: text/event-stream`

### Backend returns `200 OK` (Chunked transfer encoding)
Events are sent as text:

```text
data: {"chunk": "Sure!"}
data: {"chunk": " In Tailwind, you can"}
data: {"chunk": " use `flex`."}
data: {"status": "done", "fullMessageId": "msg_114"}
```

### Important Notes for Your Development Team

1.  **Database Separation (Normalization)**: Notice that we separated `Conversation` (thread headers) from `Messages` (chat content). This is the exact architectural decision that allows the sidebar (with potentially hundreds of chats) to load in milliseconds when the user logs in, because the heavy text payloads of the actual messages are excluded from the initial query.
2.  **Security (Ownership Validation)**: For all message-related endpoints (Section 3), the backend MUST verify that the requesting user (`request.user.id`) is the explicit owner of the requested `conversationId`. Failing to validate this tenant isolation must result in a `403 FORBIDDEN` error.
3.  **Streaming (Typing Effect)**: As outlined in Section 4, if you want your AI bot to stream its response word-by-word (simulating a typing effect like ChatGPT), you must implement Server-Sent Events (SSE) using the `text/event-stream` response type instead of a standard blocking JSON response.


