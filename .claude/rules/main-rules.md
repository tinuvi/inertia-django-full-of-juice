# Architecture Decision Record

## Testing

- **Always create tests** for every implementation.

## Logging

- Always use parameterized logging (e.g., `logger.info("Message %s", value))` and never pre-format log strings with f-strings, %, or .format().
- When you see `getLogger(__name__)`, change it `getLogger("inertia_django_full_of_juice")`

## Running tests

- Run all tests:
    ```bash
    docker compose run --remove-orphans --rm integration-tests
    ```
- When the implementation is fully completed, you can format and lint the entire codebase (you don't need to execute tests after this):
    ```bash
    docker compose run --remove-orphans --rm lint-formatter
    ```
