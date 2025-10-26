#pip install pytest pytest-django


from django.test import TestCase

# tests/test_access_control.py
import pytest

@pytest.mark.django_db
def test_menu_requires_login(client, menu_url, login_url):
    r = client.get(menu_url, follow=False)
    assert r.status_code in (301, 302)
    # Should redirect to login
    assert login_url.strip("/") in r.headers["Location"]
    # Should include 'next=' so we can bounce back after login
    assert "next=" in r.headers["Location"]

@pytest.mark.django_db
def test_menu_allows_authenticated(client_logged_in, menu_url):
    r = client_logged_in.get(menu_url)
    assert r.status_code == 200
