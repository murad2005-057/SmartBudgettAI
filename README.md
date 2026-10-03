 
## Vercel backend configuration

The Django service uses SQLite for local development. Vercel deployments must
use a persistent PostgreSQL database because deployment filesystems are
read-only and instance-local.

1. Provision a PostgreSQL database (for example, Neon through the Vercel
   Marketplace) and set its connection URL as `DATABASE_URL` in the Vercel
   project's environment variables.
2. Run Django migrations against that database before using the API:

   ```powershell
   cd backend
   $env:DATABASE_URL = "<PostgreSQL connection URL>"
   python manage.py migrate --noinput
   ```

   Keep the connection URL private; do not commit it to the repository.

The backend allows Vercel preview and production hosts for `ALLOWED_HOSTS`,
CORS, and CSRF. Registration returns JSON for unexpected server errors; the
full exception is also written to the backend logs.
