# Binance P2P Dashboard - versión con extracción inteligente

Este proyecto ya viene armado para desplegarse en **Render** con:

- **FastAPI** como aplicación web.
- **PostgreSQL** como base de datos.
- **Cron job** en Render para sincronizar órdenes Binance cada 5 minutos.
- **Dashboard web** para revisar órdenes, clientes y métricas de 6 meses.
- **Exportación Excel** con hoja de órdenes y hoja de clientes.
- **Extracción local** por regex o **extracción inteligente con OpenAI** si configuras `OPENAI_API_KEY`.

## Qué hace hoy

### Desde la API oficial de Binance C2C
- Consulta historial de órdenes con `GET /sapi/v1/c2c/orderMatch/listUserOrderHistory`.
- Guarda:
  - número de orden
  - fecha
  - comprador / nickname devuelto por Binance
  - par fiat
  - monto
  - tipo de orden
  - estado
- Calcula por cliente:
  - cantidad de transacciones últimos 6 meses
  - monto acumulado últimos 6 meses
  - primera y última transacción del período

### En el dashboard
- Permite editar la ficha del cliente:
  - RUT
  - nombres y apellidos
  - correo
  - teléfono
  - dirección
  - giro
  - segundo alias
  - notas
- Permite pegar el texto del mensaje/chat manualmente en cada orden para extraer:
  - email
  - teléfono
  - RUT
  - nombre completo
- Si `OPENAI_API_KEY` está configurada, también intenta detectar:
  - dirección
  - giro
  - segundo alias
  - resumen estructurado del mensaje

## Flujo de trabajo recomendado

1. Sincronizar órdenes desde Binance.
2. Abrir la pestaña **Órdenes**.
3. Pegar el mensaje del cliente en la orden correspondiente.
4. Guardar y detectar.
5. Revisar la ficha del cliente en **Clientes**.
6. Exportar a Excel cuando necesites consolidado.

## Estructura

```text
app/
  main.py            # FastAPI + dashboard
  sync.py            # proceso de sincronización para cron job
  models.py          # modelos SQLAlchemy
  services.py        # lógica de negocio
  ai_extractor.py    # extracción local/OpenAI
  binance_client.py  # firma HMAC y llamadas a Binance
  excel_export.py    # exportación XLSX
  parser.py          # regex y normalización
  templates/         # HTML del dashboard
  static/            # CSS
render.yaml          # blueprint de Render
requirements.txt
.env.example
```

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

- `DATABASE_URL`
- `BINANCE_API_KEY`
- `BINANCE_SECRET_KEY`
- `DASHBOARD_USERNAME`
- `DASHBOARD_PASSWORD`
- `OPENAI_API_KEY` si quieres extracción inteligente

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows usa .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Sincronización local manual

```bash
python -m app.sync
```

## Despliegue en Render

1. Subir esta carpeta a un repositorio GitHub.
2. En Render, crear un nuevo Blueprint apuntando al repo.
3. Render leerá `render.yaml` y creará:
   - web service
   - cron job
   - base de datos PostgreSQL
4. Completar variables secretas:
   - `BINANCE_API_KEY`
   - `BINANCE_SECRET_KEY`
   - `DASHBOARD_USERNAME`
   - `DASHBOARD_PASSWORD`
   - `OPENAI_API_KEY` si quieres extracción inteligente
5. Abrir el servicio web y entrar con usuario/clave HTTP Basic.

## Límite importante

La documentación pública oficial de Binance C2C sí expone historial de órdenes, pero no asumo un endpoint público para leer el chat P2P. Por eso el sistema está preparado para trabajar con el texto del mensaje cuando lo pegues en la orden o cuando luego agreguemos una fuente de texto adicional.
