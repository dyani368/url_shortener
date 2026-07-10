# FastAPI Cheat Sheet - New Learning

## Registration schemas

- Request and response schemas should be separate. A registration request accepts a
  password, but a user response must never expose the password or password hash.
- Pydantic's validated email type is `EmailStr`, not `email`.
- In Pydantic v2, `ConfigDict(from_attributes=True)` allows a schema to read fields
  from an ORM object such as a SQLAlchemy `User` instance.

## Database uniqueness and concurrent requests

- Checking whether a username or email already exists gives a friendly error, but
  it does not guarantee uniqueness.
- Two requests can perform the check before either request inserts its row. A
  database `UNIQUE` constraint is the final protection against this race condition.
- If `commit()` fails, call `rollback()` to end the failed transaction and return
  the SQLAlchemy session to a usable state. Rollback does not delete an already
  committed row.

## Useful HTTP status codes

- `201 Created`: a resource was created successfully.
- `409 Conflict`: the request conflicts with current state, such as a duplicate
  username or email.
- `422 Unprocessable Entity`: FastAPI/Pydantic could parse the request but its data
  failed validation.

## Database errors versus HTTP errors

- `sqlalchemy.exc.IntegrityError` is caught when the database rejects an operation
  because an integrity constraint was violated, such as `UNIQUE`, `FOREIGN KEY`, or
  `NOT NULL`.
- After catching an `IntegrityError` during `commit()`, call `rollback()` before
  reusing the session.
- An `IntegrityError` belongs to the database layer. The route may translate an
  expected constraint violation into an `HTTPException`, such as `409 Conflict`.
- Avoid translating every `Exception` into `409`; unrelated server failures are not
  client conflicts.
- A global FastAPI exception handler controls how a matching exception is converted
  into an HTTP response. It does not prevent a database error or automatically
  rollback a SQLAlchemy transaction.
- Local `try/except` performs translation: catch the database-layer exception where
  its meaning is known, rollback, and raise an application-layer `HTTPException`.
- Flow for a duplicate registration: PostgreSQL constraint failure -> SQLAlchemy
  `IntegrityError` -> route catches it and rolls back -> route raises HTTP `409` ->
  FastAPI (or a registered handler) formats the HTTP response.

## APIRouter mental model

- `APIRouter` is a collection of route definitions. It does not run a separate
  server.
- `app.include_router(router)` copies/attaches that router's routes to the main
  FastAPI application's route table.
- A router prefix and a decorator path are concatenated. For example, the prefix
  `/api/users` plus the route path `/register` produces `/api/users/register`.
- Route paths and prefixes must begin with `/`.
- Tags group endpoints in generated API documentation; they do not change the URL.

## Default versus custom FastAPI exception handlers

- FastAPI automatically catches `RequestValidationError` and returns a `422` JSON
  response. An API-only application normally does not need a custom validation
  handler.
- Add a custom handler only when the default response format must change, such as a
  server-rendered application that returns an HTML error page for browser routes and
  JSON for API routes.
- Request validation happens before the endpoint function runs. Invalid request data
  therefore never reaches the route body.
- Catching an exception stops that exception. If the `except` block neither raises
  nor returns, Python continues with the statement after the entire `try/except`.
  Raise an `HTTPException` when the request must stop and report an HTTP failure.

## Reading Python import tracebacks

- A highlighted import line often shows where Python entered the next module, not
  the root cause. Read the final line of the traceback first.
- If dependencies import inside the virtual environment but not with system Python,
  the application command is using the wrong interpreter. Confirm it with
  `python -c "import sys; print(sys.executable)"`.
- An `__init__.py` file marks a directory as a regular Python package and helps tools
  discover the complete import path. Without `app/__init__.py`, a CLI given
  `app/main.py` may import it as plain `main`; then absolute imports such as
  `from app.routers import auth` fail because the project root was not selected as
  the import root.

## SQLAlchemy model registration

- Defining a mapped class in a file is not enough; Python must import that module so
  SQLAlchemy can register the class and its table metadata.
- `Mapped["OtherModel"]` and `Mapped[list["OtherModel"]]` are forward references:
  the quotes delay evaluation of the type name. This helps avoid circular imports
  at runtime, but the target class still must be imported somewhere before
  SQLAlchemy configures relationships.
- If an editor says a quoted relationship type is "not defined", add a type-checking
  only import with `if TYPE_CHECKING:`. That gives the editor/type checker the class
  name without creating a runtime circular import.
- String relationship targets such as `relationship()` inferred from
  `Mapped[list["URL"]]` are resolved when SQLAlchemy configures its mappers. Both
  related model modules must have been imported by then.
- A central `app.models` package can import every mapped class once. Application code
  and Alembic can then import that package before querying models or inspecting
  `Base.metadata`.
- If a relationship target is missing or resolves to an unrelated class, SQLAlchemy
  can raise `UnmappedClassError` before executing the SQL query.
- Import style determines how a class is accessed: `from app.models import
  user_model` imports a module and requires `user_model.User`; `from
  app.models.user_model import User` imports the class directly and requires `User`.
  Mixing both styles is redundant and confusing.
- A string relationship target must match the mapped Python class name exactly. If
  the class is renamed from `URL` to `ShortUrl`, annotations such as
  `Mapped[list["URL"]]` must also be updated to `Mapped[list["ShortUrl"]]`.

## OAuth2 password login and JWT

- JWT itself does not require a particular login request format. The OAuth2 password
  token flow expects `application/x-www-form-urlencoded` fields, including
  `username` and `password`; FastAPI's `OAuth2PasswordRequestForm` parses them.
- Using that form format makes the token endpoint compatible with FastAPI's Swagger
  UI **Authorize** flow. A custom application could instead design a JSON login
  endpoint, but it would not automatically follow that OAuth2 flow.
- A conventional token response contains `access_token` and `token_type` (`bearer`).
  User profile data can be fetched through a separate authenticated `/me` endpoint.
- The JWT `sub` (subject) claim should identify the token owner. If using an integer
  database ID, encode it as a string and convert/validate it when decoding.
- `401 Unauthorized` practically means authentication is missing or invalid (bad,
  missing, or expired credentials). `403 Forbidden` means authentication succeeded,
  but that identity lacks permission for the requested action.
- A `response_model` validates, filters, and serializes the value returned by the
  endpoint; it does not invent missing values. An ORM `User` already has matching
  `id`, `username`, and `email` attributes. A newly created token is only a string,
  so the endpoint must associate it with the response fields `access_token` and
  `token_type` (using a dictionary or a `Token` schema instance).
- OAuth2 token endpoints use `POST` because credentials are submitted to create a
  token. FastAPI's Swagger OAuth2 client will call the configured `tokenUrl` with
  `POST` form data.
- In PyJWT, encoding selects one algorithm with `algorithm="HS256"`. Decoding should
  restrict accepted algorithms with an allowlist such as `algorithms=["HS256"]`;
  never trust the token itself to choose an unrestricted verification algorithm.

## Authentication dependency versus response schema

- `get_current_user()` is a dependency, not an HTTP endpoint. Defining it does not
  make it run; FastAPI calls it only when an endpoint declares
  `Depends(get_current_user)`.
- Its `-> User` annotation describes the internal Python/SQLAlchemy object returned
  to the endpoint. The endpoint's `response_model=UserResponse` separately defines
  the public HTTP representation.
- Keeping the ORM `User` internally lets protected routes use its ID, relationships,
  and database identity. The response schema then filters and serializes only fields
  intended for clients.
- Dependencies can have dependencies: a protected route requests the current user;
  `get_current_user` requests the bearer token and a database session; FastAPI
  resolves that chain before running the route body.

## Login response versus authenticated requests

- A token endpoint returning an access token does not create server-side login
  state. The client must store the token and send it on each protected request as
  `Authorization: Bearer <token>`.
- Executing `/token` manually in Swagger only displays its JSON response. Swagger
  does not automatically copy that token into future requests.
- Swagger's **Authorize** action performs the configured OAuth2 flow, stores the
  returned token in the Swagger UI client, and adds the bearer header to protected
  requests.
- The server authenticates each request independently from its credentials; it does
  not remember that the same browser previously called the login endpoint.

## URL creation schemas and storage

- A create URL request should contain only the client-owned input, usually
  `long_url`. Fields such as `short_code`, `user_id`, `click_count`, timestamps, and
  expiry are server-owned.
- Never accept `user_id` from the request body for an owned resource. Use the
  authenticated user from `Depends(get_current_user)` so a client cannot create data
  under another user's account.
- Pydantic's `HttpUrl` validates URL shape, but the database column stores a plain
  string. Convert with `str(url.long_url)` before assigning it to a SQLAlchemy
  string column.
- Python imports modules from `.py` files. If a schema file is named `url_schema`
  without the `.py` extension, `from app.schemas.url_schema import ...` will fail.
- The short code does not replace the long URL. It is stored beside the long URL as
  a lookup key. A redirect endpoint later receives the short code, finds the
  matching row, and redirects the browser to the stored long URL.
- A create endpoint can return only `short_code`, letting the frontend/client build
  the full short URL, or it can return a computed `short_url` such as
  `https://domain.com/abc123`. The database usually stores the code, not the full
  domain URL.
- Redirect endpoints are normally public: creating and managing URLs requires
  authentication, but visiting a shared short link should not require login.
- For expiration checks, compare the stored `expiry_date` with the server's current
  time. If a future-dated row returns `410 Gone`, verify the exact short code being
  visited, the running server process, and the server clock before changing the
  database model.
- Swagger UI calls endpoints using browser `fetch`. A redirect endpoint may work in
  the address bar but show "Failed to fetch" in Swagger if the redirect target is a
  different origin that does not allow Swagger's CORS request. Test redirect
  behavior by visiting the short URL directly in the browser address bar.
