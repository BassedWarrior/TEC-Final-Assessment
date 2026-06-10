# Cómo correr el backend

Guía rápida para levantar el backend de autenticación (FastAPI + PostgreSQL).

## Requisitos

- Python 3.10+
- PostgreSQL 12+
- `pip` y `venv`

## Pasos

### 1. Entorno virtual e instalar dependencias

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia el ejemplo y ajusta los valores (usuario, password, secret):

```bash
cp .env.example .env
```

> La base de datos y el rol de PostgreSQL deben existir antes. Ver detalles en `README.md`.

### 3. Crear las tablas (solo una vez)

```bash
python init_db.py
```

### 4. Levantar el servidor
(en backend/app)
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
### 5. Levantar el API del modelo
(en model/model_api)
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Verificar

- Health check: http://localhost:8000/health
- Swagger UI (docs): http://localhost:8000/docs

Endpoints disponibles: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.

> Para setup de PostgreSQL, `pg_hba.conf` y troubleshooting, ver `README.md`.
