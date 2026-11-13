# Frontend React

> Nota: la interfaz ya incluye perfilado, graficos y flujo causal. La seccion "Siguiente evolucion" de este documento es historica. Los datasets de los ejemplos no se distribuyen con el repositorio; carga uno propio desde la aplicacion.

Wokia incluye una primera interfaz React en `frontend/`. Esta interfaz consume la API FastAPI mediante el proxy `/api` configurado en Vite.

## Requisitos

Necesitas Node.js LTS instalado localmente. Comprueba que existen ambos comandos:

```powershell
node --version
npm --version
```

Si `npm` no aparece, instala Node.js LTS desde:

```text
https://nodejs.org/
```

## Ejecutar en desarrollo

Primero deja FastAPI arrancado desde la raiz del proyecto:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abre:

```text
http://127.0.0.1:5173
```

## Primera pantalla

La primera version React incluye:

- estado de conexion con la API;
- listado de datasets disponibles;
- selector de dataset;
- perfil estructural del dataset;
- metricas de filas, columnas, nulos y duplicados;
- lectura rapida de calidad;
- preview de variables numericas.

## Siguiente evolucion

Orden recomendado:

1. Integrar resumen asistido.
2. Integrar generador de graficos.
3. Integrar flujo causal por pasos.
4. Pulir sistema visual final antes de retirar Streamlit.
