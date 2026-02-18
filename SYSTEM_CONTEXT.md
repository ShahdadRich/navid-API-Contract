# SYSTEM_CONTEXT.md (The Intelligence)

## Tech Stack & Dependencies

-   **Language**: Python 3.11+
-   **Framework**: Django 5.x (Core Web Framework)
-   **API Toolkit**: Django Rest Framework (DRF)
-   **Database**: PostgreSQL (via `psycopg2-binary`)
-   **Security**:
    -   `argon2-cffi`: High-security password hashing.
    -   `django-cors-headers`: Cross-Origin Resource Sharing management.
-   **Configuration**: `python-dotenv` for environment variable management.

## Entry Points

-   **`manage.py`**: The primary CLI entry point for local development, migrations, and management commands.
-   **`config/wsgi.py`**: The entry point for WSGI-compatible web servers (e.g., Gunicorn) in production.
-   **`config/asgi.py`**: The entry point for ASGI-compatible servers (e.g., Daphne/Uvicorn) if async features are used.
-   **`config/urls.py`**: The root URL dispatcher that routes requests to specific app-level `urls.py`.

## Environment & Config

The system uses a hierarchical settings structure located in `config/settings/`:

-   **`base.py`**: Contains universal settings (Apps, Middleware, DRF config).
-   **`local.py`**: Development-specific overrides (Debug enabled, SQLite by default).
-   **`prod.py`**: Production-hardening settings (Secure cookies, restricted ALLOWED_HOSTS).

**Secrets Management**: Sensitive data like `SECRET_KEY` and database credentials are never committed. They are loaded from a `.env` file or environment variables using `load_dotenv()`.

## Database Connection

The project supports multiple database backends via Django's database engine.

-   **Local Development**: By default, the project uses **SQLite** for ease of setup. The database file is created at the project root as `db.sqlite3`.
-   **Production/Docker**: Configured to use **PostgreSQL**.
-   **How to Connect**:
    1.  Ensure `psycopg2-binary` is installed.
    2.  Define the following variables in your `.env` file:
        - `DB_NAME`: Database name.
        - `DB_USER`: Database user.
        - `DB_PASSWORD`: Database password.
        - `DB_HOST`: Database host (e.g., `localhost` or `db`).
        - `DB_PORT`: Database port (usually `5432`).
    3.  Run `python manage.py migrate` to apply schema changes.

## Frontend Integration & Connection

To connect a frontend project (e.g., React, Vue, Next.js) to this backend, follow these requirements:

### 1. CORS Configuration
Ensure the frontend origin is authorized in the `.env` file:
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend-app.com
```

### 2. Authentication (Session-based)
The backend uses Django Sessions. The frontend **must** include credentials in every request:
- **Fetch API**: `{ credentials: 'include' }`
- **Axios**: `{ withCredentials: true }`

### 3. CSRF Protection
For `POST`, `PUT`, `PATCH`, and `DELETE` requests, the frontend must:
1.  Retrieve the `csrftoken` cookie.
2.  Send it in the `X-CSRFToken` HTTP header.

### 4. API Consumption Flow
-   **Base URL**: All API calls should be prefixed with `/api/v1/`.
-   **Session Check**: On app load, the frontend should call `GET /api/v1/auth/me` to check if a user is logged in.
-   **Error Handling**: The frontend should listen for `401 Unauthorized` and redirect to the login page.

## Cross-Cutting Concerns

### Error Handling
Centralized in `core/exceptions.py` via `custom_exception_handler`. It intercepts all DRF exceptions to return a standardized JSON schema:
```json
{
  "message": "Human readable error",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

### Authentication & Authorization
-   **Strategy**: Stateful Session-based authentication (`rest_framework.authentication.SessionAuthentication`).
-   **Security**: Cookies are configured as `HttpOnly`, `SameSite='Lax'`, and `Secure` (in production) to mitigate XSS and CSRF.
-   **Permissions**: Global default is `IsAuthenticated`. Specific public endpoints (like Signup/Login) override this locally in the view.

### Rate Limiting
Configured in `base.py` under `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`. The `auth` scope is applied to sensitive endpoints to prevent brute-force attacks.

### Logging
Standard Django logging is used, typically configured in `prod.py` to output to stdout for containerized environments.
