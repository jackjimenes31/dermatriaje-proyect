release: python manage.py migrate && python manage.py seed
web: gunicorn dermatriaje.wsgi:application
