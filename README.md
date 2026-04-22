# TFG — Validador de Repositorios

Sistema de validación semántica de repositorios GitHub: los usuarios definen reglas en lenguaje natural y el sistema evalúa si el código las cumple usando LLMs y búsqueda vectorial.

## URLs locales

| Servicio         | URL                          |
|------------------|------------------------------|
| Frontend         | http://localhost:3000        |
| API / Backend    | http://localhost:8080        |
| Swagger UI       | http://localhost:8080/docs   |
| ChromaDB         | http://localhost:8000        |
| PostgreSQL       | localhost:5432 — `tfg_validator` |
| ngrok inspector  | http://localhost:4040        |

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución
- Cuenta en [Google AI Studio](https://aistudio.google.com) para obtener `GOOGLE_API_KEY`
- Cuenta en [Voyage AI](https://www.voyageai.com) para obtener `VOYAGE_API_KEY` (solo si `EMBEDDING_MODEL=voyage`)
- Cuenta en [ngrok](https://ngrok.com) para obtener `NGROK_AUTHTOKEN`
- GitHub App (para login de usuarios y validación automática en PRs)

---

## 1. Configurar variables de entorno

Copia el fichero de ejemplo y rellena los valores:

```bash
cp .env.example .env
```

### Variables obligatorias para el funcionamiento básico

```env
# GitHub App (login de usuarios — Client ID y Secret de la propia GitHub App)
GITHUB_CLIENT_ID=       # Client ID de tu GitHub App
GITHUB_CLIENT_SECRET=   # Client Secret de tu GitHub App
GITHUB_CALLBACK_URL=http://localhost:8080/auth/callback

# APIs de IA
GOOGLE_API_KEY=         # Clave de Google AI Studio
VOYAGE_API_KEY=         # Solo necesaria si EMBEDDING_MODEL=voyage

# ngrok (para recibir webhooks de GitHub en local)
NGROK_AUTHTOKEN=
```

El resto de variables tienen valores por defecto válidos para desarrollo local. Consulta `.env.example` para una descripción completa de cada una.

---

## 2. Crear la GitHub App (login y validación automática en PRs)

La GitHub App actúa como identidad del bot (publica estados en commits, hace checkout de repositorios privados) y también proporciona las credenciales OAuth para el login de usuarios.

### 2.1 Crear la app

1. Ve a **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Rellena:
   - **GitHub App name**: el nombre que quieras (p. ej. `rule-validator-tfg`)
   - **Homepage URL**: `http://localhost:3000`
   - **Callback URL**: `http://localhost:8080/auth/callback`
   - **Webhook URL**: déjalo en blanco por ahora (lo actualizarás tras arrancar ngrok)
   - **Webhook secret**: genera una cadena aleatoria segura y guárdala
3. **Permisos necesarios** (Repository permissions):
   - `Contents` → Read-only
   - `Pull requests` → Read & write
   - `Commit statuses` → Read & write
4. **Subscribe to events**: marca `Pull request` (`Installation` se activa automáticamente)
5. Crea la app y anota:
   - **App ID** (número en la página de configuración)
   - **App slug** (parte final de la URL, p. ej. `rule-validator-tfg`)
   - **Client ID** y genera un **Client Secret** (sección *OAuth credentials* de la misma página)
6. En la sección **Private keys**, genera y descarga la clave `.pem`
7. Coloca el fichero `.pem` en `backend/secrets/` (el nombre es irrelevante)

### 2.2 Configurar las variables en `.env`

```env
GITHUB_APP_ID=              # Número de App ID
GITHUB_APP_PRIVATE_KEY_PATH=/app/secrets/tu-archivo.pem
GITHUB_APP_SLUG=            # Slug de la app (p. ej. rule-validator-tfg)
GITHUB_WEBHOOK_SECRET=      # El secret que elegiste al crear la app
APPROVAL_THRESHOLD=0.8      # Puntuación mínima para aprobar el PR (0.0 – 1.0)
```

### 2.3 Actualizar la Webhook URL tras arrancar

Cuando el stack esté en marcha, ngrok genera una URL pública aleatoria. Debes apuntarla en la GitHub App:

1. Arranca el stack (ver paso 3)
2. Abre http://localhost:4040 y copia la URL `https://xxxx.ngrok-free.app`
3. Ve a **GitHub → Settings → Developer settings → GitHub Apps → tu app → Edit**
4. Pega la URL en **Webhook URL**, añadiendo el path del webhook:
   ```
   https://xxxx.ngrok-free.app/webhooks/github
   ```
5. Guarda los cambios

> **Nota**: la URL de ngrok cambia cada vez que reinicias el stack (en el plan gratuito). Repite el paso 3.3 si el webhook deja de funcionar.

---

## 3. Arrancar el stack

```bash
docker compose up --build
```

Los servicios arrancan en este orden: PostgreSQL → ChromaDB → Backend → ngrok → Frontend.

> El frontend se construye durante `docker compose up --build` (primera vez puede tardar ~1-2 min). Las variables `VITE_API_URL` y `VITE_WS_URL` se incrustan en el build; si necesitas cambiar la URL del backend, pasa los argumentos explícitamente:
> ```bash
> docker compose build frontend --build-arg VITE_API_URL=https://mi-dominio.com --build-arg VITE_WS_URL=wss://mi-dominio.com
> ```

---

## 4. Uso básico

1. Abre http://localhost:3000 y haz login con tu cuenta de GitHub
2. Si no tienes la GitHub App instalada en ningún repositorio, el front te redirigirá para instalarla; una vez instalada, los repositorios aparecerán disponibles automáticamente
3. Define las reglas de validación en lenguaje natural (p. ej. *"El proyecto debe tener un README con instrucciones de instalación"*)
4. Lanza una validación manual o abre un PR en un repositorio donde tengas la GitHub App instalada para que se ejecute automáticamente
