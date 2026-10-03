 
## Vercel backend configuration

The Django service copies `backend/db.sqlite3` to `/tmp/db.sqlite3` on Vercel
so it can write to the database despite the deployment filesystem being
read-only. This SQLite copy is temporary and local to a function instance:
user data can disappear when an instance is recycled and is not shared between
instances. Use a persistent database before relying on this deployment for
durable user data.

The backend allows Vercel preview and production hosts for `ALLOWED_HOSTS`,
CORS, and CSRF. Registration returns JSON for unexpected server errors; the
full exception is also written to the backend logs.
