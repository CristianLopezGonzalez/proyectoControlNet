# 🌊 NetFlow — Backend Django

> **Gestor de Turnos de Tarde e Intercambios con Bolsa de Días.**

NetFlow es una plataforma diseñada para gestionar cuadrántes semanales de turnos de tarde, permitiendo a los empleados solicitar intercambios de días o semanas completas con una lógica persistente de **Bolsa de Días** (saldos de deuda entre compañeros).

---

## 🚀 Características Principales

- **Gestión de Cuadrantes**: Creación y publicación de semanas de trabajo por administradores/supervisores.
- **Intercambios Inteligentes**: Solicitudes entre compañeros con validación de propiedad y estado.
- **Bolsa de Días**: Registro automático de deudas cuando un compañero cubre a otro sin devolución inmediata.
- **Auditoría Total**: Registro de toda actividad crítica (publicaciones, intercambios, ajustes de saldo).
- **Seguridad JWT**: Autenticación robusta con tokens de acceso y refresco.
- **Integración con Google Calendar**: Sincronización automática de turnos (infraestructura preparada).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
| :--- | :--- |
| **Lenguaje** | Python 3.x |
| **Framework** | Django 5.x |
| **API** | Django REST Framework (DRF) |
| **Base de Datos** | PostgreSQL (Supabase) |
| **Autenticación** | JWT (SimpleJWT) |
| **Entorno** | Virtualenv + Dotenv |

---

## 📂 Estructura del Proyecto

```bash
proyectoControlNet/
├── netflow/          # Configuración principal (settings, urls, wsgi)
├── usuarios/         # Usuario custom, roles (admin/supervisor/empleado) y Google Calendar
├── turnos/           # Calendarios semanales y asignaciones de tarde
├── intercambios/     # Lógica de solicitudes, aceptaciones y rechazos
├── bolsa/            # Gestión de saldos y movimientos de deuda entre pares
├── auditoria/        # Log de eventos del sistema (quién, qué, cuándo)
├── venv/             # Entorno virtual
└── .env              # Variables de entorno (DB, JWT, etc.)
```

---

## ⚙️ Configuración e Instalación

### 1. Clonar y preparar entorno
```bash
git clone <repo-url>
cd proyectoControlNet
python -m venv venv
source venv/Scripts/activate  # Windows
# pip install -r requirements.txt
```

### 2. Variables de Entorno (`.env`)
Configura tu archivo `.env` con los siguientes valores:
```ini
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=tu_host_supabase
DB_PORT=5432
SECRET_KEY=tu_django_secret_key
```

### 3. Migraciones y Servidor
```bash
python manage.py migrate
python manage.py runserver
```

---

## 📡 Ejemplo de Endpoints

### 🔐 Auth
- `POST /auth/login` — Login y obtención de JWT.
- `GET /auth/me` — Perfil del usuario autenticado.

### 📅 Turnos
- `GET /turnos/semanas` — Ver cuadrantes disponibles.
- `POST /turnos/asignaciones` — (Admin) Asignar turno a un usuario.

### 🔄 Intercambios
- `POST /intercambios/` — Solicitar un cambio a un compañero.
- `POST /intercambios/{id}/aceptar` — Aprueba el cambio y actualiza cuadrante + bolsa.

### 💰 Bolsa
- `GET /bolsa/saldos` — Ver a quién debes y quién te debe días.

---

## 🛡️ Lógica de Negocio Crítica

1. **Validación de Solapes**: Un usuario no puede tener dos turnos asignados el mismo día.
2. **Propiedad de Turno**: Solo el propietario de una tarde puede iniciar una solicitud de intercambio para ese día.
3. **Persistencia de Deuda**: Si el `modoCompensacion` es `bolsa`, el sistema incrementa automáticamente el contador de deuda entre los dos usuarios implicados al aceptar.
4. **Auditoría**: Cada cambio de estado en una solicitud o movimiento de bolsa genera un registro inmutable en `Auditoria`.

---

## 📧 Contacto y Soporte

Desarrollado para la gestión interna de turnos. Si tienes dudas sobre la conexión a Supabase o la lógica de la bolsa, consulta la documentación extendida en `docs/` o contacta con el administrador del sistema.