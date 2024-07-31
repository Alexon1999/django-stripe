# Setup environment

```bash
# Create a virtual environment
python3 -m venv env
````

```bash
# Activate the virtual environment
source env/bin/activate
```

```bash
# Install the requirements
pip3 install -r requirements.txt
```

```bash
# Apply the migrations
python3 manage.py migrate
```


```bash
# Run the application
python3 manage.py runserver
```

## Stripe Integration

Don't forget to Stripe Secret Key in the `django_stripe/settings.py` file.

```python
STRIPE_SECRET_KEY = 'YOUR_STRIPE_SECRET_KEY'
```