
# Django E-commerce Backend

Portfolio backend built with Django, Django REST Framework, PostgreSQL, Simple JWT, and a simulated payment provider.

## Run locally

Copy `.env.example` to `.env`, start PostgreSQL, then run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API documentation is available at `/api/docs/`, `/api/redoc/`, and `/api/schema/`.

Run checks with `python manage.py check` and tests with `python manage.py test`.

The payment provider is intentionally simulated for portfolio use; it does not process real cards or money.
