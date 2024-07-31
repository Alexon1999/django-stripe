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

## Stripe Configuration

Don't forget to Stripe Secret Key in the `django_stripe/settings.py` file.

```python
STRIPE_SECRET_KEY = 'YOUR_STRIPE_SECRET_KEY'
```

## Postman Collection for testing the API

[Postman Collection](./django-stripe.postman_collection.json)


## Frontend Applications integrated with this Django Project and Stripe Frontend Library

These are the repositories that use this Django project as a backend and Stripe Frontend Library to make payments.

- [React Native Application](https://github.com/Alexon1999/react-native-stripe)