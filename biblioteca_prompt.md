# Prompt for Claude Code: Library Management System - Unholster

## Project Context
Develop a library management web application for Unholster Chile with two user roles: Librarian and Library User. The application must be scalable, well-tested, and production-ready.

## Technology Stack
- **Backend**: Django 5.0+ with Django REST Framework
- **Database**: PostgreSQL (dockerized)
- **Frontend V1**: Django Templates + Tailwind CSS + Alpine.js
- **Frontend V2 (prepared)**: REST endpoints ready for Next.js
- **Testing**: pytest-django with minimum 80% coverage
- **Deployment**: Docker + Docker Compose on DigitalOcean Droplet
- **CI/CD**: GitHub Actions

## Project Structure

```
biblioteca/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   ├── books/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── filters.py
│   │   │   └── tests/
│   │   └── loans/
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       ├── urls.py
│   │       ├── tasks.py
│   │       └── tests/
│   ├── templates/
│   │   ├── base.html
│   │   ├── accounts/
│   │   ├── books/
│   │   └── loans/
│   ├── static/
│   ├── manage.py
│   └── requirements/
│       ├── base.txt
│       ├── development.txt
│       └── production.txt
├── docker/
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   └── nginx/
│       └── nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
└── pytest.ini
```

## Data Models

### User (extend AbstractUser)
```python
- role: CharField (choices: 'librarian', 'library_user')
- email: EmailField (unique)
- created_at, updated_at
```

### Book
```python
- isbn: CharField (unique, optional)
- title: CharField
- author: CharField
- description: TextField
- quantity: PositiveIntegerField
- available_quantity: PositiveIntegerField
- created_at, updated_at
- created_by: ForeignKey(User)
```

### Reservation
```python
- book: ForeignKey(Book)
- user: ForeignKey(User)
- reserved_at: DateTimeField
- expires_at: DateTimeField (reserved_at + 1 hour)
- status: CharField (choices: 'active', 'expired', 'converted_to_loan', 'cancelled')
- created_at, updated_at
```

### Loan
```python
- book: ForeignKey(Book)
- user: ForeignKey(User)
- reservation: ForeignKey(Reservation, nullable)
- borrowed_at: DateTimeField
- due_date: DateTimeField (borrowed_at + 2 days)
- returned_at: DateTimeField (nullable)
- status: CharField (choices: 'active', 'returned', 'overdue')
- created_at, updated_at
```

### LoanTransfer
```python
- loan: ForeignKey(Loan)
- from_user: ForeignKey(User)
- to_user: ForeignKey(User)
- transferred_at: DateTimeField
- accepted: BooleanField
- created_at
```

## Features by Role

### Librarian
- Full CRUD for books
- View all active loans
- View all active reservations
- Dashboard with basic statistics

### Library User
- Search books (by title, author, ISBN)
- Reserve book for 1 hour
- Convert reservation to loan (2 days)
- Borrow book directly (if available)
- Return book
- Share loan with another user
- View my active loans
- View my active reservations

## API Endpoints (DRF)

### Authentication
```
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/register/
GET /api/auth/me/
```

### Books
```
GET /api/books/ (list + search + pagination)
POST /api/books/ (librarian only)
GET /api/books/{id}/
PUT /api/books/{id}/ (librarian only)
DELETE /api/books/{id}/ (librarian only)
GET /api/books/{id}/availability/
```

### Reservations
```
GET /api/reservations/ (my reservations or all if librarian)
POST /api/reservations/
DELETE /api/reservations/{id}/
POST /api/reservations/{id}/convert-to-loan/
```

### Loans
```
GET /api/loans/ (my loans or all if librarian)
POST /api/loans/
POST /api/loans/{id}/return/
POST /api/loans/{id}/share/
GET /api/loans/active/
```

## Django Template Views (V1)

### Public
- Login page
- Register page

### User
- Dashboard (my loans and reservations)
- Book catalog (with search and pagination)
- Book detail
- My active loans
- My active reservations

### Librarian
- Dashboard (statistics)
- Books CRUD
- All loans list
- All reservations list

## Business Rules

1. **Reservations**:
   - Duration: 1 hour from creation
   - A user can have maximum 3 active reservations simultaneously
   - Cannot reserve an already reserved or borrowed book
   - Expired reservations are automatically marked

2. **Loans**:
   - Duration: 2 days from borrowing
   - Can be created from a reservation by the same user or directly
   - A user can have maximum 5 active loans
   - When returned, book quantity is released

3. **Loan Sharing**:
   - Original due_date is maintained
   - A transfer record is created
   - New user assumes all responsibilities

4. **Availability**:
   - available_quantity is updated with each reservation/loan
   - Restored with each return or reservation expiration

## Testing Requirements

### Minimum coverage: 80%

### Tests to implement:
- **Models**: Validations, custom methods, constraints
- **Views/ViewSets**: All endpoints (happy path and edge cases)
- **Permissions**: Verify access by role
- **Business Logic**: 
  - Reservation expiration
  - Loan/reservation limits
  - Book availability
  - Loan transfer
- **Integration Tests**: Complete user flows

### Testing command:
```bash
pytest --cov=apps --cov-report=html --cov-report=term
```

## Docker Configuration

### docker-compose.yml (development)
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: biblioteca_dev
      POSTGRES_USER: biblioteca
      POSTGRES_PASSWORD: desarrollo123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

volumes:
  postgres_data:
```

### docker-compose.prod.yml (production)
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.prod
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
    env_file:
      - .env.prod
    depends_on:
      - db
    restart: always

  nginx:
    image: nginx:alpine
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/static
      - media_volume:/app/media
    ports:
      - "80:80"
    depends_on:
      - web
    restart: always

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

## GitHub Actions CI/CD

### .github/workflows/ci-cd.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements/*.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r backend/requirements/development.txt
    
    - name: Run linting
      run: |
        pip install flake8 black isort
        flake8 backend/apps --max-line-length=120
        black --check backend/apps
        isort --check-only backend/apps
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        DJANGO_SETTINGS_MODULE: config.settings.development
      run: |
        cd backend
        pytest --cov=apps --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to DigitalOcean
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.DROPLET_HOST }}
        username: ${{ secrets.DROPLET_USERNAME }}
        key: ${{ secrets.DROPLET_SSH_KEY }}
        script: |
          cd /var/www/biblioteca
          git pull origin main
          docker-compose -f docker-compose.prod.yml down
          docker-compose -f docker-compose.prod.yml build
          docker-compose -f docker-compose.prod.yml up -d
          docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate
          docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput
```

## OAuth Preparation (django-allauth)

### Base settings:
```python
INSTALLED_APPS += [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Providers will be added later:
    # 'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.github',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Configuration to facilitate future OAuth
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
```

## Frontend (Django Templates)

### Technologies:
- Tailwind CSS (via CDN in development, build in production)
- Alpine.js for interactivity
- HTMX (optional) for dynamic updates

### Design:
- Responsive (mobile-first)
- Clear navigation between sections
- Visual feedback on actions (toasts/alerts)
- Forms with client-side and server-side validation

## Environment Variables

### .env.example
```
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://biblioteca:desarrollo123@db:5432/biblioteca_dev

# For production
# POSTGRES_DB=biblioteca_prod
# POSTGRES_USER=biblioteca
# POSTGRES_PASSWORD=secure-password-here
```

## README.md must include:

1. **Project description**
2. **Prerequisites** (Docker, Python, etc.)
3. **Local installation and setup**:
   ```bash
   # Clone repository
   # Configure .env
   # Start services with docker-compose
   # Create superuser
   # Access application
   ```
4. **Running tests**
5. **Deployment on DigitalOcean**:
   - Droplet configuration
   - Environment variables in production
   - GitHub secrets configuration
6. **Project structure**
7. **API Documentation** (link to /api/docs/)
8. **Contributing** (commit conventions, branches, etc.)

## API Documentation

Use **drf-spectacular** for OpenAPI 3.0:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Management API',
    'DESCRIPTION': 'API for library management system',
    'VERSION': '1.0.0',
}
```

Documentation endpoints:
- `/api/schema/` - OpenAPI Schema
- `/api/docs/` - Swagger UI
- `/api/redoc/` - ReDoc UI

## Code Conventions and Naming

### **CRITICAL: English Naming Convention**
- **ALL comments MUST be in English**
- **ALL variables MUST be named in English**
- **ALL functions and methods MUST be named in English**
- **ALL classes MUST be named in English**
- **ALL file names MUST be in English**
- **Docstrings in English**
- **Commit messages in English**

### Correct naming examples:
```python
# CORRECT ✓
class BookReservation(models.Model):
    """Represents a book reservation made by a library user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def is_expired(self):
        """Check if the reservation has expired."""
        current_time = timezone.now()
        return current_time > self.expires_at
    
    def get_remaining_time(self):
        """Calculate remaining time before expiration."""
        if self.is_expired():
            return timedelta(0)
        return self.expires_at - timezone.now()

# INCORRECT ✗
class ReservaLibro(models.Model):
    """Representa una reserva de libro hecha por un usuario."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    reservado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    
    def esta_expirada(self):
        """Verifica si la reserva ha expirado."""
        tiempo_actual = timezone.now()
        return tiempo_actual > self.expira_en
```

### Other conventions:
- **Commits**: Use conventional commits in English (feat:, fix:, docs:, etc.)
- **Python**: PEP 8, max line length 120
- **Imports**: Ordered with isort
- **Formatting**: Black
- **Docstrings**: Google style in English
- **Type hints**: Use where possible

### Correct commit examples:
```
feat: add book reservation model with expiration logic
fix: correct available quantity calculation on loan return
docs: update README with deployment instructions
test: add integration tests for loan sharing feature
refactor: optimize book availability query
style: format code with black and isort
chore: update dependencies to latest versions
```

## Initial Tasks

1. Create project structure
2. Configure Docker and docker-compose
3. Implement data models with migrations
4. Create authentication system
5. Implement role-based permissions
6. Develop REST API with DRF
7. Create Django templates with Tailwind
8. Implement business logic (reservations, loans, transfers)
9. Write tests with pytest
10. Configure GitHub Actions
11. Create documentation (README + API docs)
12. Prepare deployment scripts

## Deliverables

1. ✅ Complete source code in GitHub repository
2. ✅ Application running locally with Docker
3. ✅ Tests with coverage ≥80%
4. ✅ CI/CD configured in GitHub Actions
5. ✅ Complete README with instructions
6. ✅ API documented with OpenAPI/Swagger
7. ✅ Ready for deployment on DigitalOcean
8. ✅ Functional Frontend V1 with Django Templates
9. ✅ REST API ready for Next.js (V2)

---

## Final Instructions

**CRITICAL - Naming Convention**: 
- **ALL code MUST be in ENGLISH**: variables, functions, classes, comments, docstrings, file names
- **DO NOT use Spanish anywhere in the code**
- The only Spanish text allowed: end-user visible content in templates (labels, UI messages)

**IMPORTANT**: 
- Commits MUST NOT reference Claude Code or Claude
- Use conventional and descriptive commit messages in English
- Code must look like it was written by a senior engineer
- Prioritize clean, readable, and well-documented code
- Follow Django and DRF best practices
- Application must be production-ready

**Key Requirements Summary:**
- ✅ PostgreSQL 16 dockerized
- ✅ pytest with 80% minimum coverage
- ✅ Code quality checks (flake8, black, isort) in CI
- ✅ Automatic deployment to main branch only
- ✅ Simple search functionality for books
- ✅ Pagination implemented
- ✅ OpenAPI/Swagger documentation (use drf-spectacular)
- ✅ Comprehensive README
- ✅ All code, comments, and variables in English
- ✅ Ready for future OAuth integration with django-allauth

**Begin by generating the base project structure and Docker configuration files.**