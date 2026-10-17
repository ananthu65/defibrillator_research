# ARTS review application

This directory contains the deployable review application and keeps each
runtime concern isolated as the system grows.

```text
webApp/
├── frontend/   React reviewer interface
├── backend/    FastAPI service (placeholder)
├── database/   PostgreSQL migrations and initialization (placeholder)
├── ml/         Model-serving integration code (placeholder)
└── compose.yaml
```

Run the current frontend from this directory:

```sh
docker compose up --build
```

The existing research and training packages at the repository root remain the
source of truth. The `ml` directory is reserved for the application-facing
adapter or inference service rather than duplicate model-training code.
