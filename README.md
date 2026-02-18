# The Logic

## Feature Inventory

1.  **Multi-Step Signup**: Stateful registration process including email verification and profile completion.
2.  **Authentication**: Secure login/logout using Django Sessions and CSRF protection.
3.  **Onboarding**: Sequential data collection to personalize the user experience.
4.  **Session Management**: Persistence of user state via `HttpOnly` cookies.

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

## Core Components (Source of Truth)

| Feature | Primary Model | Logic Controller |
| :--- | :--- | :--- |
| **User Identity** | `apps.authentication.models.User` | `apps.authentication.models.UserManager` |
| **Signup State** | `apps.authentication.models.SignupAttempt` | `apps.authentication.services.AuthService` |
| **Onboarding Data** | `apps.onboarding.models.OnboardingProgress` | `apps.onboarding.views.OnboardingCompleteView` |

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
