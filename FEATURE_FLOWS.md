# FEATURE_FLOWS.md (The Logic)

## Feature Inventory

1.  **Multi-Step Signup**: Stateful registration process including email verification and profile completion.
2.  **Authentication**: Secure login/logout using Django Sessions and CSRF protection.
3.  **Onboarding**: Sequential data collection to personalize the user experience.
4.  **Session Management**: Persistence of user state via `HttpOnly` cookies.
5.  **AI Conversation**: Real-time messaging with AI providers (OpenAI/Gemini/Local).
6.  **Chat History**: Paginated retrieval of past conversations and messages.
7.  **Auto-Titling**: Asynchronous generation of chat titles based on context.

## Data Flow Analysis

### Multi-Step Signup Flow
The signup flow is split into multiple stages to ensure data integrity and email verification.

1.  **Entry Point**: `POST /api/v1/auth/signup/start` (`apps.authentication.views.SignupStartView`)
2.  **Logic Layer**: `AuthService.start_signup` creates a `SignupAttempt` record with an encrypted password and a temporary `signup_token`.
3.  **Verification**: `POST /api/v1/auth/signup/verify-code` checks the code against the `SignupAttempt`.
4.  **Completion**: `POST /api/v1/auth/signup/complete-profile` triggers `AuthService.complete_signup`, which validates age, creates the `User` object, and deletes the `SignupAttempt`.
5.  **Output**: Returns a session cookie and the user profile.

### Onboarding Flow
1.  **Entry Point**: `PATCH /api/v1/onboarding/progress` or `POST /api/v1/onboarding/complete`.
2.  **Middleware**: `IsAuthenticated` permission ensures the user has a valid session.
3.  **Logic Layer**: Views directly interact with `OnboardingProgress` models via `OnboardingProgressSerializer`.
4.  **Database**: Updates `OnboardingProgress` and sets `User.onboarding_complete = True` upon final submission.

### Chat & Messaging Flow
1.  **Entry Point**: `POST /api/v1/chat/conversations/{id}/messages` (Standard) or `/stream` (SSE).
2.  **Security**: `IsConversationOwner` permission validates that the user owns the thread.
3.  **Logic Layer**: `ChatService` handles message persistence and calls `LLMService` for AI responses.
4.  **Streaming**: `StreamingHttpResponse` delivers SSE chunks for a typing effect.
5.  **Background Task**: If it's the first exchange, `generate_title_task` (Celery) is triggered to update the conversation title.

## Core Components (Source of Truth)

| Feature | Primary Model | Logic Controller |
| :--- | :--- | :--- |
| **User Identity** | `apps.authentication.models.User` | `apps.authentication.models.UserManager` |
| **Signup State** | `apps.authentication.models.SignupAttempt` | `apps.authentication.services.AuthService` |
| **Onboarding Data** | `apps.onboarding.models.OnboardingProgress` | `apps.onboarding.views.OnboardingCompleteView` |
| **Chat Threads** | `apps.chat.models.Conversation` | `apps.chat.views.ConversationViewSet` |
| **Messages** | `apps.chat.models.Message` | `apps.chat.services.chat_service.ChatService` |

## Mermaid Diagrams

### Signup Process Flowchart

```mermaid
graph TD
    A[Signup Start] --> B{Email Exists?}
    B -- Yes --> C[Return 409 Conflict]
    B -- No --> D[Create SignupAttempt]
    D --> E[Send Verification Code]
    E --> F[Verify Code]
    F -- Invalid --> G[Return 400 Error]
    F -- Valid --> H[Complete Profile]
    H -- Under 18 --> I[Return 422 Underage]
    H -- Success --> J[Create User & Start Session]
    J --> K[Delete SignupAttempt]
```

### Chat & AI Interaction Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend (DRF)
    participant CS as ChatService
    participant LLM as LLM Provider
    participant CL as Celery Worker

    FE->>BE: POST /messages (content)
    BE->>CS: create_user_message()
    CS->>BE: User message saved
    BE->>CS: get_ai_response()
    CS->>LLM: Fetch completion
    LLM-->>CS: Completion text
    CS->>CS: Save AI Message
    CS-->>BE: AI Message object
    BE-->>FE: 200 OK (JSON)
    CS->>CL: Trigger generate_title_task
    CL->>LLM: Summarize first message
    LLM-->>CL: Title text
    CL->>CL: Update Conversation Title
```

### Authentication & Session Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend (DRF)
    participant DB as Database

    FE->>BE: POST /login (credentials)
    BE->>DB: Validate User
    DB-->>BE: User found
    BE->>BE: Generate Session
    BE-->>FE: 200 OK + Set-Cookie (session)
    FE->>BE: GET /me (Cookie included)
    BE->>BE: SessionAuthentication Middleware
    BE-->>FE: 200 OK (User JSON)
```
