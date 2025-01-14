# Treasure Hunt Game 🗺️

A web-based treasure hunt platform built with Django that allows users to create and participate in engaging treasure hunts. The application is containerized with Docker and deployed on AWS App Runner.

## Main Features 🌟

### For Treasure Hunt Creators 🎨

- **Customized Creation**: Design unique scavenger hunts with:
  - Title and description
  - Main image
  - Completion deadline
  - Sequential clues
  - Reference images for each clue
  - Personalized unlock messages

- **Scoring System**:
  - Assign points for each completed clue
  - Set bonus points for completing the entire hunt
  - Customize the congratulatory message

- **Privacy**:
  - Option to create public or private hunts
  - Control over who can participate

### For Players 🎮

- **Participation**:
  - Join public hunts
  - Follow sequential clues
  - Unlock new clues by solving the previous ones
  - Earn points for each solved clue

- **Progress**:
  - Visual progress bar
  - Accumulated points counter
  - Clue resolution history
  - Completion statistics

- **Intuitive Interface**:
  - Responsive design
  - Upload reference images
  - Feedback messages
  - Simple navigation system

>[!WARNING] Permissions in Django for Creating Hunts  
>Users with the `Core|treasure hunt|Can create treasure hunts` permission can create treasure hunts.



## Tech Stack 💻

- **Backend**: Django 5.1.4
- **Database**: PostgreSQL with pgvector
- **Cloud Services**: AWS (ECR, App Runner, S3)
- **Container**: Docker
- **Dependencies**: See requirements.txt for full list

## Prerequisites 📋

- Python 3.8 or higher
- Docker (for containerized deployment)
- PostgreSQL
- AWS Account (for deployment)

## Local Development Setup 🚀

1. Clone the repository:
```bash
git clone https://github.com/cmauec/treasure-hunt
cd treasure-hunt
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

## Docker Deployment 🐳

1. Build the Docker image:
```bash
docker build -t treasure-hunt .
```

2. Run the container:
```bash
docker run -p 8000:8000 treasure-hunt
```

## Environment Variables 🔐

Copy `.env.example` to `.env` and configure the following variables:

- `DATABASE_NAME`: Name of the database
- `DATABASE_USER`: Database user name
- `DATABASE_PASSWORD`: Database user password
- `DATABASE_HOST`: Host where the database is located
- `DATABASE_PORT`: Port for the database connection
- `SECRET_KEY`: Django secret key
- `AWS_ACCESS_KEY_ID`: AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key
- `AWS_STORAGE_BUCKET_NAME`: AWS S3 bucket name
- `AWS_S3_REGION_NAME`: AWS S3 region name
- `ALLOWED_HOSTS`: List of allowed hosts for the application
- `CSRF_TRUSTED_ORIGINS`: List of trusted origins for CSRF protection


