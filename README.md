# UMass-SmartDine-Finder
CS 520 Project

# How to run
```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip django
git clone https://github.com/simon-andrews/umass-toolkit.git
cd umass-toolkit
python setup.py install
cd ..
rm -rf umass-toolkit
pip install psycopg2 openai bs4 pint requests
export OPENAI_API_KEY="<PUT YOUR KEY HERE>"
python manage.py migrate
python manage.py runserver
```

In case of failure when installing psycopg2 on mac:
```
pip install psycopg2-binary
```

This is the branch we will bring our final changes to.
Please create a branch from this branch and make changes from there.
Before bringing anything on main, we will make sure everything is working and running on the dev branch.

# 🧭 Work Breakdown — SmartDine Finder (1-Day Sprint)

## 🎯 Objective
Deliver two demo-ready features using Django with LLM-assisted development:
1. **Login & Register (MVP)**
2. **Menu & Info Center (Basic)**

Each feature is handled by an independent developer. All tasks are designed to be completed in parallel.

---

## 🔹 Feature A — Login & Register (MVP)

### **Goal**
Enable users to create an account, log in, access the menu page, and log out securely.

### **Scope**
- Email + password registration and login.
- Session persistence using Django auth.
- Simple, server-rendered templates for forms.
- Error handling and access protection for menu pages.

---

### **Tasks**

#### 🧩 A1 — Authentication Backend
**Developer:** Dev 1  
**Description:**
- Enable `django.contrib.auth` and sessions.
- Implement views for `/register`, `/login`, `/logout` using Django’s `UserCreationForm` and `AuthenticationForm`.
- Configure redirects (`LOGIN_REDIRECT_URL = '/menu/'`, `LOGOUT_REDIRECT_URL = '/login/'`).
- Handle duplicate email, invalid credentials, and CSRF.

**Deliverables:**
- Fully functional registration and login views.
- User session persists after login and clears on logout.

---

#### 🧩 A2 — Authentication Templates
**Developer:** Dev 2  
**Description:**
- Create templates: `base.html`, `login.html`, `register.html`.
- Add a navigation bar that dynamically shows “Login” or “Logout” based on auth state.
- Include form field validation and styled error messages.
- Add redirects to `/menu/` after successful login.

**Deliverables:**
- Working frontend forms integrated with A1 backend.
- Clean layout, responsive forms, and user feedback for errors.

---

#### 🧩 A3 — Access Control and Session Management
**Developer:** Dev 3  
**Description:**
- Protect `/menu/` route using Django’s `@login_required` decorator.
- Configure middleware for CSRF and session.
- Add logout button functionality.
- Ensure unauthorized access redirects to `/login/`.

**Deliverables:**
- Access control enforced correctly.
- Session behavior verified (persist, expire, logout).

---

## 🔹 Feature B — Menu & Info Center (Basic)

### **Goal**
Show a list of dining halls with hours, open/closed status, and meals for breakfast, lunch, and dinner.

### **Scope**
- Mock dining data for 3 halls.
- API endpoint `/api/menus/` returning JSON.
- `/menu/` page displaying hall cards with meals and open/closed indicators.

---

### **Tasks**

#### 🧩 B1 — Menu API (Mock Data)
**Developer:** Dev 4  
**Description:**
- Create a Django app `menus` with route `/api/menus/`.
- Use a fixture (`menus.json`) containing 3 dining halls with meals and hours.
- Compute `is_open` based on the current time and hall hours.
- Return a structured JSON:
  ```json
  [
    {
      "hallName": "Hamp",
      "hours": "07:00-20:00",
      "isOpen": true,
      "meals": {
        "breakfast": ["Oatmeal", "Scrambled Eggs"],
        "lunch": ["Veg Curry", "Rice"],
        "dinner": ["Pasta", "Salad"]
      }
    }
  ]
  ```

**Deliverables:**
- Working `/api/menus/` endpoint with correct schema.
- Graceful handling for empty or missing meals.

---

#### 🧩 B2 — Menu Page Template
**Developer:** Dev 5  
**Description:**
- Create `/menu/` view to fetch data from `/api/menus/` or load from fixture directly.
- Build `menu.html` with hall cards showing:
  - Hall name and hours.
  - Open/Closed badge.
  - Collapsible sections for Breakfast, Lunch, and Dinner.
- Handle empty data and error messages gracefully.

**Deliverables:**
- Fully functional menu page displaying all mock halls and meals.
- Error and empty states handled cleanly.

---

## ✅ Final Deliverables
- **Login & Register**: complete flow from registration to logout with sessions.
- **Menu & Info Center**: 3 dining halls displayed with mock menu data and open/closed status.
- **Protected Routes**: menu page accessible only after login.
- **Stable Demo**: end-to-end run from sign-up → login → menu → logout.
