# AI Label Maker Backend

## Overview

Backend service for the AI Label Maker application, providing API endpoints for label generation, management, and processing.

## Features

- Label generation using AI models
- RESTful API endpoints
- Database management
- User authentication
- File processing and storage

## Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

## Running Locally

1. Set up environment variables in `.env` file
2. Run database migrations: `python manage.py migrate`
3. Start the development server: `python manage.py runserver`
4. Access the API at `http://localhost:8000`

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

- Runs on push to `main` and pull requests
- Executes unit tests and linting checks
- Builds and pushes Docker image to registry on successful merge
- Deploys to staging environment automatically

See `.github/workflows/` for workflow configuration.
