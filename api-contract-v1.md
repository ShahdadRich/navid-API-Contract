# Navid API Contract v1 (Auth + Onboarding Only)

Audience: Shahdad, Alireza\
Scope: This version intentionally includes only auth and onboarding endpoints.

---

## 1) Base URL and Versioning

All endpoints are versioned and prefixed with:

`/api/v1`

Examples:

- `/api/v1/auth/me`
- `/api/v1/onboarding/complete`

---

## 2) Global Conventions

## 2.1 Content Types

- JSON request/response for all endpoints in this document.

## 2.2 Error Body (all non-2xx)

```json
{
  "message": "Human readable message",
  "code": "MACHINE_CODE",
  "details": {}
}
```

`message` should always be present.

## 2.3 Date Format

- Timestamps: ISO-8601 (`2026-02-16T10:20:30.000Z`)
- `birthDate` in API requests: `YYYY-MM-DD`

## 2.4 Session Object

```json
{
  "userId": "usr_123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "onboardingComplete": false
}
```

---

## 3) Session Cookie (Important)

Your frontend uses cookie-based auth. The browser stores the cookie and sends it automatically.

## 3.1 Login/Signup success response must include `Set-Cookie`

Example response header:

```http
Set-Cookie: session=SESSION_ID_OR_JWT; Path=/api; HttpOnly; SameSite=Lax; Max-Age=1209600; Secure
```

Recommended attributes:

- `HttpOnly`: required (prevents JS access to cookie).
- `Path=/api`: required.
- `SameSite=Lax` (or `None` if truly cross-site).
- `Secure`: required in production HTTPS.
- `Max-Age` or `Expires`: define session lifetime.

## 3.2 Browser request header (automatic)

Frontend does not manually set cookie header. Browser sends:

```http
Cookie: session=SESSION_ID_OR_JWT
```

when `fetch(..., { credentials: "include" })` is used (already done in frontend).

## 3.3 CORS requirements (if frontend and backend are different origins)

Backend must set:

- `Access-Control-Allow-Origin: https://your-frontend-domain` (not `*`)
- `Access-Control-Allow-Credentials: true`
- `Vary: Origin`

And allow methods/headers used by frontend.

## 3.4 Logout cookie clearing

On logout, return `204` and clear cookie:

```http
Set-Cookie: session=; Path=/api; HttpOnly; Max-Age=0; SameSite=Lax; Secure
```

## 3.5 CSRF note

Because auth uses cookies, protect state-changing endpoints (`POST/PATCH/DELETE`) with CSRF strategy:

- Django CSRF middleware + CSRF token header, or
- equivalent robust CSRF protection.

## 3.6 Frontend behavior

- Frontend never reads the session cookie directly.
- Frontend checks login state using `GET /api/v1/auth/me`.

---

## 4) Auth Endpoints

Signup flow in frontend:

1. email
2. password
3. email code verification
4. full name + birth date (18+)
5. redirect to onboarding

## 4.1 Start Signup

`POST /api/v1/auth/signup/start`

### Frontend sends

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

### Backend returns `201`

```json
{
  "signupToken": "st_abc123",
  "email": "user@example.com",
  "verification": {
    "channel": "email",
    "codeLength": 6,
    "expiresAt": "2026-02-16T10:35:00.000Z",
    "resendAvailableAt": "2026-02-16T10:21:00.000Z"
  },
}
```

### Errors

- `400 VALIDATION_ERROR`
- `409 EMAIL_ALREADY_EXISTS`

## 4.2 Resend Signup Code

`POST /api/v1/auth/signup/resend-code`

### Frontend sends

```json
{
  "signupToken": "st_abc123"
}
```

### Backend returns

- `204 No Content`

### Errors

- `410 SIGNUP_TOKEN_EXPIRED`
- `429 RATE_LIMITED`

## 4.3 Verify Signup Code

`POST /api/v1/auth/signup/verify-code`

### Frontend sends

```json
{
  "signupToken": "st_abc123",
  "code": "123456"
}
```

### Backend returns `200`

```json
{
  "signupToken": "st_abc123",
  "emailVerified": true,
}
```

### Errors

- `400 INVALID_CODE`
- `410 CODE_EXPIRED`

## 4.4 Complete Signup Profile

`POST /api/v1/auth/signup/complete-profile`

### Frontend sends

```json
{
  "signupToken": "st_abc123",
  "fullName": "Jane Doe",
  "birthDate": "2000-08-24"
}
```

### Backend behavior

- Validate age >= 18 based on current date.
- Create/activate account.
- Set session cookie (`Set-Cookie`).

### Backend returns `201`

```json
{
  "userId": "usr_123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "onboardingComplete": false
}
```

### Errors

- `422 UNDERAGE` with message:
  - `"You must be at least 18 years old to use Navid AI."`
- `400 VALIDATION_ERROR`
- `410 SIGNUP_TOKEN_EXPIRED`

## 4.5 Login

`POST /api/v1/auth/login`

### Frontend sends

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

### Backend behavior

- Validate credentials.
- Set session cookie (`Set-Cookie`).

### Backend returns `200`

```json
{
  "userId": "usr_123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "onboardingComplete": true
}
```

### Errors

- `401 INVALID_CREDENTIALS`

## 4.6 Session Check

`GET /api/v1/auth/me`

### Frontend sends

- No body; browser sends session cookie automatically.

### Backend returns `200`

Either:

```json
null
```

or session object:

```json
{
  "userId": "usr_123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "onboardingComplete": true
}
```

## 4.7 Logout

`POST /api/v1/auth/logout`

### Frontend sends

- No body.

### Backend behavior

- Invalidate server session.
- Clear session cookie.

### Backend returns

- `204 No Content`

## 4.8 Forgot Password

`POST /api/v1/auth/forgot-password`

### Frontend sends

```json
{
  "email": "user@example.com"
}
```

### Backend returns

- `204 No Content` (even if email does not exist)

## 4.9 Reset Password

`POST /api/v1/auth/reset-password`

### Frontend sends

```json
{
  "token": "reset-token",
  "password": "new-strong-password"
}
```

### Backend returns

- `204 No Content`

### Errors

- `400 INVALID_TOKEN`

---

## 5) Onboarding Endpoints

Onboarding is separate from auth and requires authenticated session cookie.

## 5.1 Save Onboarding Progress (optional)

`PATCH /api/v1/onboarding/progress`

### Frontend sends

```json
{
  "intent": "work",
  "goals": ["code", "data", "brainstorm"]
}
```

### Backend returns `200`

```json
{
  "intent": "work",
  "goals": ["code", "data", "brainstorm"],
  "onboardingComplete": false
}
```

### Errors

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`

## 5.2 Complete Onboarding

`POST /api/v1/onboarding/complete`

### Frontend sends

```json
{
  "intent": "work",
  "goals": ["code", "data", "brainstorm"]
}
```

### Backend behavior

- Persist onboarding answers.
- Mark onboarding as complete.

### Backend returns `200`

```json
{
  "userId": "usr_123",
  "email": "user@example.com",
  "name": "Jane Doe",
  "onboardingComplete": true
}
```

### Errors

- `400 VALIDATION_ERROR`
- `401 UNAUTHORIZED`

---

## 6) Status Codes (Quick Reference)

- `200` success with JSON body
- `201` created
- `204` success with no body
- `400` validation/request issue
- `401` unauthenticated
- `403` forbidden
- `404` not found
- `409` conflict
- `410` expired token/code
- `422` semantic validation (example: underage)
- `429` rate limit
- `500` unexpected server error
