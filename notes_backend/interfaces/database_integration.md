# Database Integration for notes_backend

This backend is designed to work with an external database service (container `notes_database`). All APIs for users and notes assume persistent storage.

## Integration Points

To connect to the external database:

- Replace instances of `FakeDB.*` in `src/api/main.py` with ORM/database client code for:
  - Creating/fetching users by email (`users` table/model)
  - Creating, listing, getting, updating, and deleting notes by user (`notes` table/model)

## Environment Variables

Required environment variables for DB should be supplied by orchestration or .env, such as:
- `NOTES_DB_URL` (Database connection string)
- `NOTES_DB_USER` (If applicable)
- `NOTES_DB_PASSWORD` (If applicable)
- etc.

## Migration steps

1. Swap out the `FakeDB` implementation for your production ORM/queries.
2. Use FastAPI dependency injection to provide DB sessions to endpoint functions if using SQLAlchemy/etc.
3. Test all endpoints with the live DB.

## Security

- User passwords are always hashed with bcrypt (see code).
- JWT signing key (`JWT_SECRET_KEY`) should be provided via a secure environment variable.

## Extensibility

You can add more fields to User or Note models by editing `src/api/main.py` models.
