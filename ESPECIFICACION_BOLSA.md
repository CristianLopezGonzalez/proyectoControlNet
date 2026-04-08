# Arquitectura: Sistema de Bolsa e Intercambios (Guía Front-End)

Este documento resume el funcionamiento interno del sistema de Bolsa de Días y los Intercambios, así como los JSON exactos que el Frontend debe enviar, va a recibir, y cómo sabe lo que tiene que dibujar en los calendarios de la interfaz.

---

## 1. El Concepto Base: Deuda de Días

El sistema no utiliza un "banco de horas", sino que pivota bajo el concepto de **deuda entre compañeros pares**. 
Si el **Empleado A** le cubre un turno al **Empleado B** (y acuerdan el modo de compensación `"bolsa"`), el sistema registrará silenciosamente que el **Empleado A tiene 1 día a favor del Empleado B**. 

La base de datos almacena esto normalizado (`A` siempre es el ID menor, `B` el ID mayor), pero hacia el Frontend se lo servimos de manera totalmente transparente.

---

## 2. Flujo 1: Pedir un Intercambio

El solicitante va al Frontend (a su cuadrante semanal) y decide ceder su turno de tarde a un compañero (el receptor).

**Ruta:** `POST /intercambios/`

**Payload enviado por el Front (JSON):**
```json
{
  "tipo": "dia", 
  "receptor": 15, // ID del compañero
  "asignacion_origen": 204, // ID de mi turno que le estoy cediendo
  "asignacion_destino": null, // (Opcional) Si me traigo uno suyo a cambio
  "modo_compensacion": "bolsa", // Clave para que si lo acepta, B me deba 1 día
  "motivo": "Necesito la tarde libre"
}
```

*Cuando el receptor hace un `POST /intercambios/123/aceptar/`, el sistema transfiere el turno y suma 1 día de deuda al receptor hacia el solicitante.*

---

## 3. ¿Cómo sabe el Frontend lo que tiene que "pintar" en el Calendario?

Cuando el Frontend carga las solicitudes enviadas o recibidas con un `GET /intercambios/mias/`, el backend **NO** devuelve un simple ID desnudo (`204`) para la capa de presentación. 

Gracias a los *Serializers* anidados, el JSON entregado al Front-End inyecta todos los desgloses en tiempo real. Dentro del objeto de la solicitud, el Front encontrará `asignacion_origen_detalle`, el cual contiene **qué día de la semana, las fechas exactas de esa semana y las horas asociadas**.

**Ejemplo de lo que extrae el Front en la recepción:**
```json
{
  "id": 123,
  "tipo": "dia",
  "modo_compensacion": "bolsa",
  "asignacion_origen": 204, // El ID en Base de datos 
  "asignacion_origen_detalle": {
      "id": 204,
      "dia": "lunes", 
      "semana_detalle": {
          "numero_semana": 14,
          "fecha_inicio_semana": "2026-04-06",
          "fecha_fin_semana": "2026-04-12"
      },
      "turno_plantilla_detalle": {
          "nombre": "Tarde",
          "hora_inicio": "15:00:00", 
          "hora_fin": "23:00:00"
      }
  }
}
```
**Conclusión para "pintar":** Con este JSON, la aplicación cliente sabe instantáneamente que ese intercambio corresponde al bloque de "Lunes 6 de Abril de 15h a 23h" y puede acomodar visualmente la petición flotando sobre ese hueco en el calendario del receptor.

---

## 4. Flujo 2: Comprobar mi Estado en la Bolsa

El usuario ahora quiere ver a quién debe días o quién se los debe a él.

**Ruta:** `GET /bolsa/saldos/`

**Respuesta recibida por el Front (JSON):**
```json
[
  {
    "id": 12,
    "usuario_a": 4,  
    "usuario_a_detalle": { "id": 4, "nombre": "Antonio López" },
    "usuario_b": 15,
    "usuario_b_detalle": { "id": 15, "nombre": "Marta Gómez" },
    "saldo_dias_a_favor_de_a": 1, // Marta le debe 1 día a Antonio
    "saldo_dias_a_favor_de_b": 0, // Antonio no le debe días a Marta
    "ultima_actualizacion": "2026-04-07T12:00:00Z"
  }
]
```

Para ver la **"Libreta del Banco"** con las entradas y salidas de días:
**Ruta:** `GET /bolsa/movimientos/`

```json
[
  {
    "id": 89,
    "saldo": 12,
    "origen_usuario": 15,
    "origen_usuario_detalle": { "id": 15, "nombre": "Marta Gómez" },
    "destino_usuario": 4,
    "dias": 1,
    "tipo": "genera_deuda", // Puede ser "genera_deuda" o "compensa_deuda"
    "fecha": "2026-04-07T12:00:00Z"
  }
]
```

---

## 5. Flujo 3: Tramitar Compensación de Deudas

Marta (ID 15) está de buen humor y decide que le va a regalar a Antonio uno de los días que ella le debía recuperar, cancelando así su deuda (sin necesidad de atarlo a un turno físico concreto, pactado fuera del horario normal). Inicia una propuesta de compensación asíncrona.

**Ruta:** `POST /bolsa/compensar/`

**Payload enviado por el Front (JSON):**
```json
{
  "usuario_destino_id": 4, // ID de Antonio a quien Marta le debe días
  "dias": 1
}
```

**Atención Front-End: ¿Por qué esta petición no lleva turno ni tiene impacto gráfico en el Calendario?**
La ruta `/bolsa/compensar/` es puramente un concepto matemático. Trámite administrativo. Se descuenta una ficha "simbólica" del saldo. 
- Al tener `'dias': 1` y no ir atado a ninguna asignación física de horas, **no se dibuja o resta ningún bloque del calendario**. 
- Si Marta quisiera "pagarle la deuda" trabajándole un turno físico concreto a Antonio, **NO usaría este endpoint**, usaría el Flujo 1 normal (solicitando cubrirle un turno un Lunes y enviando `modo_compensacion="bolsa"` para pagar).

**La respuesta del sistema del POST /bolsa/compensar/ (JSON):**
```json
{
  "id": 19,
  "solicitante": 15,
  "receptor": 4,
  "dias": 1,
  "estado": "pendiente",
  "fecha_creacion": "2026-04-07T12:05:00Z"
}
```

### Completando la compensación

Unos días más tarde, Antonio verifica su sistema, su Front llama a `GET /bolsa/compensar/` y detecta la propuesta. Él pulsa "Aceptar" en la interfaz.

**Ruta:** `POST /bolsa/compensar/19/aceptar/`

*A nivel interno, el saldo favorable de Antonio baja automáticamente de `1` a `0`. Se genera el recibo del movimiento en bolsa (`compensa_deuda`), se ajustan las tablas de saldo y se cierra la auditoría asépticamente, sin tocar la renderización de cuadrantes (ya que no hubo turno negociado).*
