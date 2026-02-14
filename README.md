# haruna-api-2025

## About

This application is the back-end API for the HarunaDB project.

The application's namesake is derived from the
battleship [Haruna](https://en.wikipedia.org/wiki/Japanese_battleship_Haruna).

## Project specification

- FastAPI
- Supabase

## System requirement

- Python 3.14
- uv package and project manager
- Docker

## Project setup for development

### Install dependencies using uv

```shell
uv sync
```

### Set up environment variablesSet up environment variables

- Copy the example environment file using:

```shell
cp .env.example .env
```

- Edit `.env` and fill in your configuration values

### Running the Development Server

```shell
uvicorn app.main:app --reload
```

- The API will be available at: `http://localhost:8000`
- The `--reload` flag enables auto-restart when code changes are detected
- All changes to Python files in the `app/` directory will trigger an automatic reload
- Check the console output for any startup errors or warnings

## Code quality

```shell
ruff format
```

## Deploying to Fly.io

This project is ready to run on Fly.io using the included `Dockerfile` and `fly.toml`.

### Prerequisites

- Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
- Have a Fly.io account and be logged in: `fly auth login`

### Deploy

- (Optional) Configure secrets (for any env values you need): `fly secrets set KEY=value OTHER=value`
- From the project root, run: `fly deploy`
- Open the app in your browser: `fly open`

### Notes:

- The service listens on internal port 8080 (mapped to 80/443 externally). `PORT=8080` is set in `fly.toml` and the
  scontainer.
- The app uses `pydantic-settings`; environment variables can override defaults in `app/core/config.py`.
- Scale memory/CPU (example): `fly scale vm shared-cpu-1x --memory 256`
- Set min/max machines via `fly scale count` or adjust autoscaling in `fly.toml`.

## Local build/run

- Build: `docker build -t haruna-api-2025 .`
- Run: `docker run -p 8080:8080 haruna-api-2025`
- The app will be available at: `http://localhost:8080/`
