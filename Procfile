web: gunicorn -c "python:config.gunicorn" --reload "app.app:create_app()"
celery: celery worker -B -l info -A app.blueprints.contact.tasks