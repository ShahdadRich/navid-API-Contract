# PROJECT_STRUCTURE.md (The Map)

## Visual Tree

```text
.
├── apps/                        # Business Logic Modules
│   ├── authentication/          # User Auth & Identity Management
│   │   ├── migrations/
│   │   ├── apps.py
│   │   ├── models.py            # User and SignupAttempt models
│   │   ├── serializers.py       # DRF Serializers for Auth
│   │   ├── services.py          # Business logic for Auth
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py             # Auth API endpoints
│   └── onboarding/              # User Onboarding Logic
│       ├── migrations/
│       ├── apps.py
│       ├── models.py            # OnboardingProgress model
│       ├── serializers.py
│       ├── urls.py
│       └── views.py
│   └── chat/                    # Chat & History Logic
│       ├── migrations/
│       ├── services/            # Service Layer (Chat, LLM)
│       ├── apps.py
│       ├── models.py            # Conversation and Message models
│       ├── pagination.py        # Cursor and PageNumber pagination
│       ├── permissions.py       # IsConversationOwner
│       ├── serializers.py
│       ├── tasks.py             # Celery tasks (Auto-titling)
│       ├── urls.py
│       └── views.py             # Chat API endpoints
├── config/                      # Project Configuration
│   ├── settings/                # Django Settings (split by env)
│   │   ├── base.py
│   │   ├── local.py
│   │   └── prod.py
│   ├── asgi.py
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py
├── core/                        # Shared Infrastructure & Utilities
│   ├── exceptions.py            # Global Exception Handler
│   └── __init__.py
├── manage.py                    # Django CLI entry point
├── requirements.txt             # Python Dependencies
├── api-contract-v1.md           # API Specification
└── openapi.yaml                 # OpenAPI/Swagger Definition
```

## Directory Responsibilities

| Directory | Primary Responsibility |
| :--- | :--- |
| `apps/` | Contains all modular business logic. Each subdirectory is a Django app. |
| `apps/authentication/` | Handles user registration, multi-step signup, login, and session management. |
| `apps/onboarding/` | Manages post-signup user data collection and progress tracking. |
| `apps/chat/` | Handles AI conversations, thread history, and background auto-titling. |
| `config/` | Root configuration, routing, and deployment entry points. |
| `config/settings/` | Environment-specific configuration using a base/inheritance pattern. |
| `core/` | Shared utilities, custom middleware, and global exception handlers used across all apps. |

## Architecture Pattern: Service Layer & Modular Monolith

The project follows a **Modular Monolith** architecture with a distinct **Service Layer** for complex business logic.

- **Modular Monolith**: Features are grouped into isolated Django applications (`apps/`) to maintain high cohesion and low coupling.
- **Service Layer**: Business logic (especially in `authentication`) is extracted from views into `services.py`. This ensures logic is reusable, testable, and separate from the HTTP request/response handling.
- **DRF Views & Serializers**: Standard Django Rest Framework patterns are used for data validation and API response formatting.

## Naming Conventions

- **Apps**: Plural or descriptive nouns in `apps/` (e.g., `authentication`, `onboarding`).
- **Models**: Singular PascalCase (e.g., `User`, `SignupAttempt`).
- **Services**: Classes named `FeatureService` (e.g., `AuthService`) or standalone functions in `services.py`.
- **Views**: PascalCase ending in `View` (e.g., `OnboardingCompleteView`).
- **Tests**: Prefixed with `test_` or in `tests.py`.
- **Files**: snake_case for all Python files.
