# Library Management System - Unholster Chile

A comprehensive library management web application built with Django and Django REST Framework. The system supports two user roles (Librarian and Library User) and provides full functionality for book management, reservations, and loans.

## Features

### For Library Users
- Browse and search books by title, author, or ISBN
- Reserve books for 1 hour
- Convert reservations to 2-day loans
- Borrow books directly (if available)
- Return borrowed books
- Share/transfer loans with other users
- View active loans and reservations

### For Librarians
- Full CRUD operations for books
- View all active loans and reservations
- Dashboard with library statistics
- User management capabilities

## Technology Stack

- **Backend**: Django 5.0+ with Django REST Framework
- **Database**: PostgreSQL 16 (Dockerized)
- **Frontend V1**: Django Templates + Tailwind CSS + Alpine.js
- **Frontend V2**: REST API ready for Next.js integration
- **Testing**: pytest-django with 80% minimum coverage
- **Deployment**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **API Documentation**: OpenAPI 3.0 with drf-spectacular

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development without Docker)
- Git

## Project Structure

```
biblioteca/
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # CI/CD pipeline configuration
├── backend/
│   ├── config/
│   │   ├── settings/          # Django settings (base, dev, prod)
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/          # User authentication and management
│   │   ├── books/             # Book management
│   │   └── loans/             # Reservations, loans, and transfers
│   ├── templates/             # Django templates
│   ├── static/                # Static files
│   ├── requirements/          # Python dependencies
│   └── manage.py
├── docker/
│   ├── Dockerfile.dev         # Development Docker image
│   ├── Dockerfile.prod        # Production Docker image
│   └── nginx/
│       └── nginx.conf         # Nginx configuration for production
├── docker-compose.yml         # Development environment
├── docker-compose.prod.yml    # Production environment
├── .env.example               # Environment variables template
├── .gitignore
└── README.md
```

## Local Installation and Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd biblioteca
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` file if needed. The default values work for local development.

### 3. Start Services with Docker Compose

```bash
# Build and start containers
docker-compose up -d

# Wait for services to be healthy (check logs)
docker-compose logs -f
```

### 4. Run Migrations

```bash
docker-compose exec web python manage.py migrate
```

### 5. Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 6. Access the Application

- **Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **API Schema**: http://localhost:8000/api/schema/

## Running Tests

### Run All Tests

```bash
docker-compose exec web pytest
```

### Run Tests with Coverage

```bash
docker-compose exec web pytest --cov=apps --cov-report=html --cov-report=term
```

Coverage report will be available in `backend/htmlcov/index.html`.

### Run Specific Tests

```bash
# Test a specific app
docker-compose exec web pytest apps/accounts/tests/

# Test a specific file
docker-compose exec web pytest apps/books/tests/test_models.py

# Test a specific test
docker-compose exec web pytest apps/books/tests/test_models.py::TestBookModel::test_create_book
```

### Run with Code Quality Checks

```bash
# Linting
docker-compose exec web flake8 apps --max-line-length=120 --exclude=migrations

# Code formatting check
docker-compose exec web black --check apps --exclude=migrations

# Import sorting check
docker-compose exec web isort --check-only apps --skip migrations
```

## API Endpoints

### Authentication
```
POST   /api/auth/register/          # Register new user
POST   /api/auth/login/             # Login user
POST   /api/auth/logout/            # Logout user
GET    /api/auth/me/                # Get current user info
POST   /api/auth/users/change-password/  # Change password
```

### Books
```
GET    /api/books/                  # List all books (with search/filter)
POST   /api/books/                  # Create book (librarian only)
GET    /api/books/{id}/             # Get book details
PUT    /api/books/{id}/             # Update book (librarian only)
PATCH  /api/books/{id}/             # Partial update (librarian only)
DELETE /api/books/{id}/             # Delete book (librarian only)
GET    /api/books/{id}/availability/ # Check book availability
```

### Reservations
```
GET    /api/loans/reservations/     # List reservations
POST   /api/loans/reservations/     # Create reservation
GET    /api/loans/reservations/{id}/ # Get reservation details
DELETE /api/loans/reservations/{id}/ # Cancel reservation
POST   /api/loans/reservations/{id}/convert-to-loan/ # Convert to loan
```

### Loans
```
GET    /api/loans/loans/            # List loans
POST   /api/loans/loans/            # Create loan
GET    /api/loans/loans/{id}/       # Get loan details
POST   /api/loans/loans/{id}/return_book/ # Return book
POST   /api/loans/loans/{id}/share/ # Transfer loan to another user
GET    /api/loans/loans/active/     # Get active loans
```

### Loan Transfers
```
GET    /api/loans/transfers/        # List loan transfers
GET    /api/loans/transfers/{id}/   # Get transfer details
```

## Business Rules

### Reservations
- Duration: 1 hour from creation
- Maximum 3 active reservations per user
- Cannot reserve already reserved or borrowed books
- Expired reservations are automatically marked

### Loans
- Duration: 2 days from borrowing
- Maximum 5 active loans per user
- Can be created from a reservation or directly
- Book quantity is released when returned

### Loan Sharing
- Original due date is maintained
- Transfer record is created
- New user assumes all responsibilities

## Deployment on DigitalOcean

### 1. Droplet Configuration

Create a Ubuntu 22.04 droplet and install Docker:

```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin
```

### 2. Clone Repository

```bash
cd /var/www
git clone <repository-url> biblioteca
cd biblioteca
```

### 3. Configure Production Environment

```bash
cp .env.example .env.prod
nano .env.prod
```

Set production values:
```
DEBUG=False
SECRET_KEY=your-secure-random-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://biblioteca:secure-password@db:5432/biblioteca_prod
POSTGRES_DB=biblioteca_prod
POSTGRES_USER=biblioteca
POSTGRES_PASSWORD=secure-password
```

### 4. Deploy Application

```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 5. Configure GitHub Secrets for CI/CD

In your GitHub repository, go to Settings > Secrets and add:

- `DROPLET_HOST`: Your droplet IP address
- `DROPLET_USERNAME`: SSH username (usually `root`)
- `DROPLET_SSH_KEY`: Private SSH key for authentication

### 6. Nginx Configuration (Optional)

For SSL/TLS and custom domain, configure Nginx on your host machine or use the built-in nginx service.

## Development Workflow

### Adding New Features

1. Create a new branch
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and test
```bash
docker-compose exec web pytest
```

3. Check code quality
```bash
docker-compose exec web flake8 apps --max-line-length=120
docker-compose exec web black apps
docker-compose exec web isort apps
```

4. Commit with conventional commits
```bash
git commit -m "feat: add new feature description"
```

5. Push and create pull request
```bash
git push origin feature/your-feature-name
```

### Commit Convention

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `style:` Code formatting
- `chore:` Maintenance tasks

## Contributing

1. Fork the repository
2. Create your feature branch
3. Ensure tests pass and coverage is ≥80%
4. Follow code conventions (PEP 8, max line length 120)
5. Write meaningful commit messages
6. Submit a pull request

## Code Quality Standards

- **Python**: PEP 8 compliance
- **Line Length**: Maximum 120 characters
- **Formatting**: Black
- **Import Sorting**: isort
- **Linting**: flake8
- **Test Coverage**: Minimum 80%
- **Docstrings**: Google style
- **Type Hints**: Encouraged where appropriate

## Future Enhancements

- OAuth integration (Google, GitHub) via django-allauth
- Next.js frontend (API already prepared)
- Email notifications for overdue books
- Advanced search with Elasticsearch
- Book cover images
- Rating and review system
- Mobile app with React Native

## License

This project is proprietary software developed for Unholster Chile.

## Support

For issues and questions, please contact the development team or create an issue in the repository.

---

Built with ❤️ for Unholster Chile
