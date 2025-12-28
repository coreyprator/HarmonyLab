# HarmonyLab

Harmonic progression training system for jazz standards.

## Development Methodology

This project follows [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5

## Architecture

- **Backend**: FastAPI on Cloud Run
- **Database**: MS SQL Server on Cloud SQL
- **Credentials**: Google Secret Manager
- **CI/CD**: GitHub Actions

## Development Workflow

```
Write Code → Push to GitHub → GitHub Actions → Cloud Run → Test
```

**NO LOCALHOST DEVELOPMENT** - All testing happens on Cloud Run URL.

## Deployment

Automatic on push to `main` branch.

### Get Cloud Run URL

```bash
gcloud run services describe harmonylab --region=us-central1 --format="value(status.url)"
```

### Manual Deploy (if needed)

```bash
gcloud run deploy harmonylab \
  --source . \
  --region us-central1 \
  --project super-flashcards-475210
```

## API Documentation

Production: `https://[CLOUD_RUN_URL]/docs`

## Health Check

```bash
curl https://[CLOUD_RUN_URL]/health
```

## GCP Resources

| Resource | Value |
|----------|-------|
| Project | `super-flashcards-475210` |
| Cloud SQL Instance | `flashcards-db` |
| Database | `HarmonyLab` |
| Secret Prefix | `harmonylab-*` |
| Region | `us-central1` |

## Project Structure

```
Harmony-Lab/
├── app/
│   ├── api/
│   │   └── routes/         # API endpoint definitions
│   ├── db/                 # Database connection and queries
│   ├── models/             # Pydantic models
│   └── services/           # Business logic (MIDI parsing, etc.)
├── config/                 # Configuration files
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
├── Dockerfile              # Container definition
├── main.py                 # FastAPI application entry point
└── requirements.txt        # Python dependencies
```

## Documentation

- [Kickoff Document](HarmonyLab-Kickoff.md) - Full project vision and requirements
- [Infrastructure Setup](harmony-lab-infra-setup.md) - GCP setup instructions
- [Schema](HarmonyLab-Schema-v1.0.sql) - Database schema
- [Cloud Migration](HARMONYLAB-CLOUD-MIGRATION.md) - Deployment guide

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: MS SQL Server (Cloud SQL)
- **MIDI Parser**: mido
- **MusicXML Parser**: music21 (planned)
- **Hosting**: Google Cloud Run
- **Frontend**: Vanilla JavaScript (planned)

