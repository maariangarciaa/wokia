import json
import os
from pathlib import Path
import pandas as pd
import re

BASE_DIR = Path("auto_doc/files")
BASE_DIR.mkdir(parents=True, exist_ok=True) 

def generar_prompt_variables_relacionadas(pregunta_usuario: str) -> str:
    return f"""
Rol:
Eres un asistente experto en análisis causal aplicado a datos tabulares (DataFrame en pandas). El DataFrame ya ha sido cargado y contiene múltiples columnas con distintos nombres.

Tarea:
Dado que el usuario ha formulado una pregunta causal en lenguaje natural, debes:

1. **Inferir la variable objetivo (dependiente)** a partir del texto de la pregunta, aunque el nombre exacto no coincida. Por ejemplo, si el usuario pregunta "¿Qué afecta a la velocidad?", y existe una columna llamada `TopSpeed`, deberías deducir que esa es la variable objetivo más probable.
2. **Buscar todas las columnas numéricas** del DataFrame y calcular la correlación de cada una con la variable objetivo identificada.
3. **Seleccionar solo aquellas variables con correlación fuerte**: mayor que 0.7 o menor que -0.7.
4. **Devolver el resultado en JSON**, con el nombre de la columna objetivo real y las variables candidatas más correlacionadas.

Reglas para usar herramientas:
- Usa primero la herramienta `find_candidate_variables` con la pregunta causal completa del usuario. Esa herramienta ya identifica objetivo, calcula correlaciones y devuelve JSON valido.
- Si `find_candidate_variables` devuelve un JSON valido, no uses mas herramientas y devuelvelo inmediatamente como `Final Answer:` en JSON estricto con comillas dobles.
- No llames a `python_repl_ast` despues de usar `find_candidate_variables`.
- Primero consulta `list(df.columns)` y `df.select_dtypes(include='number').columns.tolist()`.
- Para localizar una columna objetivo por nombre, usa una expresion simple, por ejemplo: `next((col for col in df.columns if 'PriceEuro' in col), None)`.
- No escribas bucles `for` completos en una sola linea dentro de `Action Input`.
- Si una accion devuelve `SyntaxError`, no repitas el mismo codigo; cambia a una expresion simple.

Formato de salida esperado (en JSON, sin explicaciones adicionales):
{{
  "objetivo": "NombreExactoDeLaColumnaObjetivo",
  "candidatas": ["Var1", "Var2", "Var3"]
}}

Pregunta del usuario:
\"\"\"{pregunta_usuario}\"\"\"
"""

def generar_descripcion_dataset(df: pd.DataFrame) -> str:
    descripcion = []

    for col in df.columns:
        tipo = df[col].dtype
        if tipo == 'object' or df[col].nunique() < 15:
            valores = df[col].unique().tolist()
            descripcion.append(f"- {col} (categórica): valores únicos = {valores}")
        elif pd.api.types.is_numeric_dtype(df[col]):
            descripcion.append(f"- {col} (numérica): media = {df[col].mean():.2f}, min = {df[col].min()}, max = {df[col].max()}")
        else:
            descripcion.append(f"- {col} (tipo {tipo})")

    return "\\n".join(descripcion)

def generar_prompt_hipotesis(variable_objetivo: str, variable_independiente: str, df_info: str) -> str:
    return f"""
Contexto:
Estás trabajando con un dataset tabular en pandas con columnas numéricas y categóricas. A continuación se muestra un resumen del dataset con estadísticas clave por variable:

{df_info}

Rol:
Eres un experto en causalidad y analítica de datos aplicada. Estás ayudando a un usuario hispanohablante a formular **hipótesis causales claras y accionables** entre una variable candidata (posible causa) y una variable objetivo (efecto observado).

Idioma:
**Todas las hipótesis deben estar escritas exclusivamente en español.**

Objetivo:
Formula entre 2 y 3 **hipótesis causales** que:
- Usen un lenguaje claro, natural y en **español**.
- Tengan **criterios explícitos** que permitan implementar una columna binaria de tratamiento.
- **Incluyan entre paréntesis el nombre exacto de las variables involucradas según el DataFrame** (por ejemplo: `Price_USD`, `MaxSpeed_KmH`).
- Sean coherentes con la estadística y el sentido común del dominio.

Reglas clave:
- La dirección causal debe ser: **{variable_independiente} → {variable_objetivo}**.
- Si {variable_independiente} es numérica, **propón umbrales concretos** (por ejemplo: “mayor a 180 km/h”).
- Si es categórica, **menciona claramente los valores de la categoría** (por ejemplo: “si el tipo de carrocería es SUV”).
- Evita términos vagos como “alta”, “elevado” o “lujoso” si no están definidos por datos.
- Cada hipótesis debe poder traducirse en una línea de código binaria, por ejemplo:
  - `df["treatment"] = df["TopSpeed_KmH"] > 180`
  - `df["treatment"] = df["BodyType"] == "SUV"`

Ejemplos correctos:
- “Los vehículos cuya velocidad máxima supera los 200 (TopSpeed_KmH) tienden a tener precios más altos (Price_USD).”
- “Los modelos de la marca Tesla (Make) presentan precios más elevados (Price_USD) que los de otras marcas.”
- “Los coches que pesan más de 1800 kg (Weight_Kg) suelen tener un coste superior (Price_USD).”

Ejemplos incorrectos:
- “Los vehículos rápidos son más caros.” ❌ (no es accionable)
- “La velocidad afecta al precio.” ❌ (demasiado vago)
- “Las marcas lujosas tienden a ser más costosas.” ❌ (¿qué es lujosa?)

Resultado esperado:
Una lista de 2 o 3 hipótesis causales escritas en **español**, en lenguaje natural, con **criterios claros y cuantificables** y **nombres de variables entre paréntesis** según aparecen en el DataFrame. 
Reglas de uso de herramientas:
- No uses `find_candidate_variables`: la variable candidata y la variable objetivo ya han sido seleccionadas.
- No uses formato ReAct. No escribas `Thought:`, `Action:`, `Action Input:`, `Observation:` ni `Final Answer:`.
- Responde directamente con una lista de 2 o 3 hipotesis.
"""

def generar_prompt_codigo_tratamiento(hipotesis: str) -> str:
    return f"""
Objetivo:
A partir de la siguiente hipótesis causal escrita en lenguaje natural, genera código Python en pandas que cree una nueva columna binaria llamada `treatment` en un DataFrame llamado `df`.

Hipótesis:
\"\"\"{hipotesis}\"\"\"

Contexto del dataset:
- El DataFrame `df` ya ha sido cargado.
- Accede a los nombres de las columnas del `df` para saber qué variables contiene y tener mayor contexto.
- Usa **únicamente estas columnas** del `df` para razonar cuál representa la variable causal (independiente). NO inventes ninguna.
- Es posible que la hipótesis utilice términos como "precio" o "peso del vehículo" en lugar del nombre real de columna (por ejemplo: `TotalPrice`, `Weight_kg`).

Tu trabajo:
1. Determina si la hipótesis se puede traducir en una condición binaria basada solo en **una columna existente en `df`**.
2. Si es así, genera el código Python necesario para crear `df["treatment"]`.
3. Indica claramente **qué columna(s)** se usaron para construir `treatment`, y asegúrate de **eliminarlas del DataFrame** después de crear la nueva columna.
4. Si no es posible mapear la hipótesis a una columna o no es binarizable, devuelve el JSON de error.

🚫 Prohibido:
- No generes datos.
- No uses estructuras como `pd.DataFrame(...)`.
- No uses la variable dependiente como parte de la condición.
- No inventes nombres de columna que no existen.

Instrucciones:
- Si puedes generar código, devuelve un JSON con:
Reglas finales:
- Puedes usar `python_repl_ast` solo para inspeccionar columnas o tipos de datos.
- No ejecutes el codigo final que crea `df["treatment"]`; el codigo final debe ir dentro del JSON.
- Cuando tengas identificada la columna y la regla binaria, termina con `Final Answer:` y devuelve solo el JSON.

```json
{{
  "explicacion": "Texto explicando la lógica de la columna `treatment` en español.",
  "codigo": "Código Python que crea la columna treatment en df y elimina la(s) columna(s) que se usaron para construirla"
}}
```
"""

def limpiar_codigo_agente(texto: str) -> str:
    """
    Extrae el bloque de código de una respuesta del agente que puede estar envuelta en ```python ... ```
    """
    if "```" in texto:
        # Extraer lo que está entre los backticks
        bloques = re.findall(r"```(?:python)?(.*?)```", texto, re.DOTALL)
        if bloques:
            return bloques[0].strip()
    return texto.strip()

def generar_prompt_dag_con_datos(resumen: dict) -> str:
    tratamiento = resumen["treatment"]
    outcome = resumen["outcome"]
    top_corr = resumen["correlaciones"]
    conf_cat = resumen["confusoras_categoricas"]

    return f"""
Objetivo:
Eres un experto en inferencia causal. Tu tarea es construir un **DAG (Gráfico Acíclico Dirigido)** en formato DOT para representar las relaciones causales del dataset, y devolverlo en un bloque DOT válido, limpio y sin errores.

Contexto:
- Variable de tratamiento: `{tratamiento}`
- Variable de resultado: `{outcome}`
- Variables numéricas correlacionadas con `{outcome}` (posibles mediadores):  
{json.dumps(top_corr, indent=2)}

- Variables categóricas con p < 0.05 (posibles confundidores):  
{json.dumps(conf_cat, indent=2)}

Herramienta disponible:
Usa exclusivamente la herramienta `generate_dag`, que recibe un JSON con esta estructura:

```json
{{
  "treatment": "{tratamiento}",
  "outcome": "{outcome}",
  "correlaciones": {json.dumps(top_corr)},
  "confusoras_categoricas": {json.dumps(conf_cat)}
}}
```

Instrucciones estrictas:
- Llama a generate_dag con el JSON anterior.
- Asegúrate de que el grafo generado es acíclico. Si detectas un ciclo, corrige las flechas para que el DAG sea válido.
- No inventes relaciones que no estén justificadas.
- Cada nodo debe tener un estilo específico:
    - Tratamiento: [style=filled, fillcolor=lightgreen]
    - Resultado: [style=filled, fillcolor=lightgrey]
    - Confusores: [style=filled, fillcolor=orange]
    - Mediadores: [style=filled, fillcolor=lightblue]

🚫 No debes:
- Generar el DAG manualmente.
- Incluir explicaciones ni texto fuera del bloque DOT.
- Enviar backticks (```) ni etiquetas Markdown.

Resultado esperado:
Devuelve exclusivamente el bloque DOT limpio, como este ejemplo:

digraph {{
treatment [style=filled, fillcolor=lightgreen];
PriceEuro [style=filled, fillcolor=lightgrey];
Brand [style=filled, fillcolor=orange];
TopSpeed_KmH [style=filled, fillcolor=lightblue];

Brand -> treatment;
Brand -> PriceEuro;
treatment -> TopSpeed_KmH;
TopSpeed_KmH -> PriceEuro;
treatment -> PriceEuro;
}}

Antes de devolver el resultado:
Verifica que el grafo no contenga ciclos.
"""

def generar_prompt_identificacion_efecto_seguro():
    return """
Objetivo:
Eres un experto en inferencia causal usando el paquete `dowhy`. Tu tarea es determinar si el modelo causal cargado es **identificable** con los datos actuales y explicar los resultados de forma clara, profesional y estructurada.

Contexto:
Ya existe un modelo causal llamado `model` que fue creado con:
- Un DataFrame real llamado `df`
- Una columna de tratamiento llamada `treatment`
- Una variable de resultado llamada `outcome`
- Un grafo causal confirmado por el usuario

Herramienta disponible:
Puedes usar la herramienta `identify_causal_effect`, que ya está registrada. Esta herramienta:
- Ejecuta `model.identify_effect()`
- Devuelve el tipo de estimando causal
- Extrae las variables necesarias para el ajuste con `get_backdoor_variables()`

Instrucciones:
1. Llama a la herramienta `identify_causal_effect`.
2. Espera el resultado, que incluye:
   - El tipo de estimando causal (`backdoor`, `frontdoor`, `iv`, etc.)
   - Las variables necesarias para el ajuste (lista de nombres)
3. Redacta una **explicación clara en español** que incluya:
   - Si el efecto fue identificado correctamente
   - Qué criterio se usó
   - Qué variables se deben usar para el ajuste
   - Qué se debería hacer si el efecto no fuera identificable

Formato de respuesta (únicamente este bloque JSON):
Devuelve **solo** el siguiente bloque JSON, sin etiquetas Markdown, sin comillas adicionales y sin backticks:

{
  "criterio": "backdoor",
  "backdoor_variables": ["Var1", "Var2", "Var3"],
  "justificacion": "Texto claro y profesional en español que explique si el efecto fue identificado, bajo qué criterio y por qué las variables listadas permiten un ajuste válido."
}

-> Importante: Después de usar `identify_causal_effect`, asegúrate de que el estimando identificado sea almacenado en `st.session_state["identified_estimand"]` para permitir su uso posterior en `estimate_causal_effect_tool`.

🚫 Prohibido:
- No incluyas backticks (ni ``` ni ````).
- No uses etiquetas como `json`, `python`, ni Markdown.
- No devuelvas texto fuera del bloque JSON.
- No uses Markdown ni encabezados.
- No incluyas código Python.
- No generes explicaciones fuera del campo justificacion.

- Solo devuelve el JSON como texto plano, válido y bien formateado.

Recuerda:
Tu único rol es analizar y resumir correctamente el resultado de la herramienta en el JSON.
"""

def generar_prompt_recomendar_metodo_critico(treatment_col: str, backdoor_vars: list) -> str:
    return f"""
Rol:
Eres un **experto en inferencia causal aplicada** y tienes acceso directo a un DataFrame pandas 'df'. Ya se ha definido una columna binaria `{treatment_col}` como **tratamiento**, y se ha identificado el siguiente conjunto de **variables de ajuste (backdoor)**: {backdoor_vars}

Objetivo:
Analizar críticamente el dataset y **recomendar el mejor método de estimación causal** entre los disponibles en la librería `DoWhy`. Tu análisis debe tener en cuenta la naturaleza de las variables, el tamaño de muestra y los supuestos de cada método.

---

🔍 Métodos disponibles y análisis crítico:

1. **`backdoor.linear_regression`**: Estima el efecto causal de un tratamiento sobre un resultado usando regresión lineal, ajustando por un conjunto de variables confusoras.
   
   ¿Cuándo usarlo?
   * Hay confusores observables conocidos (identificados mediante un grafo causal o conocimiento experto).
   * Se asume una relación lineal o aproximadamente lineal entre las variables.
   * El tamaño de muestra es grande y se quiere una estimación rápida y sencilla.
   * El objetivo es una estimación promedio global del efecto (ATE).
   * No hay evidencia clara de interacción o no linealidad importante entre variables.

   ¿Cuándo NO usarlo?
   * Existen confusores no observados (violación del backdoor).
   * La relación entre el tratamiento y el resultado es no lineal o altamente compleja.
   * Hay colinealidad fuerte entre covariables (puede inflar varianzas).
   * El número de covariables es muy grande en relación al tamaño de muestra.
   * El modelo lineal no ajusta bien (mala especificación, alta heterocedasticidad, etc.).

   Limitaciones:
   * Supone que todas las relaciones relevantes son capturadas por una forma lineal.
   * No captura interacciones complejas o efectos heterogéneos.
   * Puede ser sesgado si no se incluyen todas las variables del conjunto de ajuste correcto.

---

2. **`backdoor.distance_matching`**: Estima el efecto causal emparejando unidades tratadas y no tratadas que tengan valores similares en las variables confusoras, usando una métrica de distancia (como distancia Euclidiana o de Mahalanobis).

    ¿Cuándo usarlo?
    * Cuando se tienen confusores observables bien medidos y se desea evitar suposiciones paramétricas.
    * Si el investigador desea mantener la interpretación intuitiva de comparar unidades "similares".
    * En estudios con tamaño de muestra moderado y un número manejable de covariables.
    * Cuando la relación entre covariables y resultado no se asume lineal.

    ¿Cuándo NO usarlo?
    * Cuando hay alta dimensionalidad (muchas covariables), lo que dificulta encontrar buenos emparejamientos.
    * Si la distancia entre unidades tratadas y de control es grande (mal emparejamiento).
    * Cuando hay escasez de controles parecidos para las unidades tratadas (o viceversa).
    * En presencia de confusores no observados (viola el supuesto de ignorabilidad condicional).

    Limitaciones:
    * Puede descartar muchas unidades si no se encuentran buenos pares (reduce poder estadístico).
    * Sensible a la elección de la métrica de distancia.
    * No estima efectos globales si los matches son locales y heterogéneos

---

3. **`backdoor.propensity_score_stratification`**: Estima el efecto causal agrupando las unidades en estratos (o bloques) según su score de propensión —la probabilidad de recibir el tratamiento dado los confusores— y comparando los resultados dentro de cada estrato.

   ¿Cuándo usarlo?
   * Cuando se puede estimar un score de propensión confiable a partir de los confusores observados.
   * Si se quiere reducir el sesgo de selección sin asumir una forma funcional específica para el resultado.
   * En contextos con una cantidad moderada de datos y buena superposición entre tratados y no tratados.
   * Cuando se desea una estimación ajustada del efecto promedio (ATE), pero manteniendo cierta flexibilidad.

   ¿Cuándo NO usarlo?
   * Cuando el modelo de score de propensión está mal especificado o no balancea bien los covariables.
   * Si hay poca superposición (overlap) entre grupos tratados y no tratados (estratos mal definidos).
   * Cuando hay pocos datos: los estratos pueden ser demasiado pequeños para estimar efectos confiables.
   * En presencia de confusores no observados.

   Limitaciones:
   * Depende de una buena estimación del score de propensión.
   * Puede haber heterogeneidad dentro de los estratos que no se corrige completamente.
   * No adecuado si el número de estratos es demasiado bajo (subajuste) o demasiado alto (ruido).

---

4. **`backdoor.propensity_score_matching`**: Estima el efecto causal emparejando unidades tratadas con no tratadas que tienen scores de propensión similares, lo que busca balancear los confusores observados entre grupos.

   ¿Cuándo usarlo?
   * Cuando se puede estimar un score de propensión robusto a partir de covariables observadas.
   * Si se desea hacer comparaciones directas entre unidades tratadas y no tratadas similares.
   * En estudios observacionales con buena superposición de scores entre grupos.
   * Cuando se busca una estimación del efecto promedio en las unidades tratadas (ATT).

   ¿Cuándo NO usarlo?
   * Cuando hay baja superposición entre los scores de propensión (pocos matches posibles).
   * Si el modelo del score de propensión está mal especificado (no balancea bien los grupos).
   * Cuando se pierde demasiada información debido al descarte de unidades no emparejadas.
   * En presencia de confusores no observados.

   Limitaciones:
   * No siempre usa toda la muestra (puede eliminar unidades sin match).
   * La calidad del emparejamiento depende completamente del modelo de propensión.
   * No controla por diferencias residuales post-matching a menos que se combine con regresión (matching + adjustment).

---

5. **`backdoor.propensity_score_weighting`**: Estima el efecto causal asignando a cada unidad un peso inversamente proporcional a su probabilidad de recibir el tratamiento (score de propensión), para crear una muestra pseudo-populacional balanceada.

   ¿Cuándo usarlo?
   * Cuando se busca una estimación del efecto promedio (ATE) usando toda la muestra.
   * Si se puede estimar con precisión el score de propensión.
   * Cuando se quiere evitar el descarte de unidades que ocurre en métodos de emparejamiento.
   * En estudios con buena superposición entre tratados y no tratados (overlap).

   ¿Cuándo NO usarlo?
   * Cuando el modelo de propensión produce scores extremos cercanos a 0 o 1 (pesos inestables).
   * Si hay poca superposición entre los grupos (lo que genera alta varianza).
   * Cuando el tamaño de muestra es pequeño (los pesos grandes pueden sesgar los resultados).
   * En presencia de confusores no observados o score mal especificado.

   Limitaciones:
   * Muy sensible a scores de propensión extremos (inflan varianza e inestabilidad).
   * Requiere diagnóstico posterior (verificación de balance después de aplicar los pesos).
   * El resultado depende en gran medida de la calidad del modelo de score.

---

6. **`iv.instrumental_variable`**: Estima el efecto causal utilizando una **variable instrumental (IV)**, es decir, una variable que afecta al tratamiento pero no afecta directamente al resultado (solo a través del tratamiento) y no está relacionada con confusores no observados.

   ¿Cuándo usarlo?
   * Cuando se sospecha la existencia de confusores no observados que hacen inválidos los métodos de ajuste directo (como backdoor).
   * Si se dispone de un instrumento válido que cumple las condiciones de relevancia y validez (independencia y exclusión).
   * Cuando se desea estimar el **efecto causal local** en la subpoblación afectada por el instrumento (LATE).
   * En contextos donde la asignación al tratamiento está parcialmente determinada por una política, incentivo o factor externo.

   ¿Cuándo NO usarlo?
   * Cuando no se tiene un instrumento válido (por ejemplo, el IV está correlacionado con confusores o afecta directamente el resultado).
   * Si el instrumento es débil (tiene poca influencia sobre el tratamiento).
   * Cuando se desea estimar un efecto global (ATE), pero el IV solo identifica un efecto local.
   * En muestras pequeñas, donde la varianza del estimador puede ser muy alta.

   Limitaciones:
   * Difícil encontrar instrumentos verdaderamente válidos en la práctica.
   * Estima un efecto **local** (LATE), no necesariamente aplicable a toda la población.
   * Resultados sensibles a violaciones del supuesto de exclusión.

---

7. **`iv.regression_discontinuity`**: Estima el efecto causal aprovechando una regla de asignación basada en un umbral (discontinuidad), donde el tratamiento se asigna si una variable (por ejemplo, edad, puntaje, ingreso) cruza un punto de corte específico.

   ¿Cuándo usarlo?
   * Cuando existe una **regla clara y exógena** de asignación al tratamiento basada en un umbral.
   * Si se tiene acceso a datos justo antes y después del punto de corte (alta densidad de observaciones cerca del umbral).
   * Cuando se busca una estimación creíble del efecto causal local (LATE) alrededor del umbral.
   * En entornos donde se aplican políticas o programas con criterios de elegibilidad estrictos.

   ¿Cuándo NO usarlo?
   * Cuando no existe una discontinuidad clara o la regla de asignación no se cumple rigurosamente (manipulación del umbral).
   * Si los individuos pueden influir su posición respecto al umbral (violación de aleatorización implícita).
   * Cuando los datos cerca del umbral son escasos o muy ruidosos.
   * Si se desea una estimación del efecto en toda la población (no solo en el vecindario del umbral).

   Limitaciones:
   * Solo estima el efecto local cerca del punto de corte (no generalizable).
   * Requiere muchos datos alrededor del umbral para ser estadísticamente potente.
   * Supone que otros factores no cambian bruscamente en el mismo umbral (lo que puede invalidar la identificación).

---
-> Fase 1: Ejecutar diagnóstico (versión corregida)
Antes de tomar cualquier decisión, debes ejecutar la herramienta llamada diagnostico_causal_df_tool.

Esta herramienta espera un único diccionario como argumento, con las siguientes claves:
    - "treatment_col": una cadena con el nombre de la columna binaria de tratamiento (por ejemplo: "treatment").
    - "backdoor_vars": una lista con los nombres de las variables de ajuste (confusoras) identificadas.

Ejemplo correcto de invocación:
Action: diagnostico_causal_df_tool
Action Input: {{
  "treatment_col": "treatment",
  "backdoor_vars": ["x", "y", "z"]
}}

El resultado será un JSON que contiene:
    - Medidas de balance entre grupos (diferencia_media_estandarizada, cramers_v)
    - Diagnóstico del score de propensión (auc, extremos, overlap_visual)
    - Sugerencias automáticas en recomendaciones_metodologicas

---

-> Fase 2: Recomendación
Una vez que obtengas ese JSON (almacenado en una variable llamada diagnostico), analiza cuidadosamente sus valores para decidir:
    - Si es apropiado usar regresión (requiere balance).
    - Si matching o IPW son viables (requieren buen overlap y sin scores extremos).
    - Si el score es poco útil o hay desbalance fuerte, evita esos métodos.

🚫 No uses ningún método si el diagnóstico lo desaconseja.

Nota: Si existe evidencia o sospecha de **efectos heterogéneos** del tratamiento (por ejemplo, diferentes efectos según grupos o covariables), evita métodos como `linear_regression` simples y considera:
    - Agregar interacciones entre tratamiento y covariables,
    - Estratificación por subgrupos,
    - O modelos más flexibles si están disponibles.

⚠️ AUC muy alto (> 0.9): Aunque puede parecer bueno, en inferencia causal esto suele indicar **pobre solapamiento** entre tratados y controles, lo que desaconseja el uso de `matching` o `IPW` debido a inestabilidad o falta de comparables.
⚠️ Si el número de variables (o categorías de variables) es alto respecto al tamaño de muestra, `linear_regression` puede generar modelos inestables o con varianzas infladas. Considera técnicas de reducción o penalización si persistes en usar regresión.

Importante: Si usas `linear_regression` y las covariables de ajuste son categóricas, **deben ser codificadas correctamente** (por ejemplo, con one-hot encoding) antes de ajustar el modelo.

❌ Si ningún método es viable (por ejemplo, hay mal solapamiento, scores extremos o confusores no observados), puedes devolver:
    - Una advertencia indicando que **no es posible estimar un efecto causal confiable** con los datos actuales.
    - O sugerir explorar métodos alternativos como `iv.instrumental_variable` si hay posibles instrumentos válidos.

---

-> Instrucciones para la salida
Devuelve un único bloque de código Python (python_repl_ast) donde:

    - Asumes que ya tienes el resultado de la herramienta en una variable llamada diagnostico.
    - Lees sus valores clave.
    - Decides el mejor método causal disponible y lo justificas.
    - Usas print(json.dumps(...)) para devolver un diccionario con:
    - "metodo_recomendado": nombre del método sugerido (ej. "backdoor.linear_regression").
    - "justificacion": explicación profesional en español, en formato Markdown con puntos. Debe ser clara para personas no expertas en causalidad.

Ejemplo del formato esperado:
{{
  "metodo_recomendado": "backdoor.linear_regression",
  "justificacion": "**Resumen:** se recomienda regresión lineal ajustada porque es la opción más prudente para este diagnóstico.\n\n**Diagnóstico del dataset:**\n- **Balance de grupos:** indica cuántas observaciones tratadas y de control hay, y si el reparto está desbalanceado.\n- **Score de propensión:** explica el AUC con lenguaje sencillo y por qué un AUC muy alto puede ser una señal de poca comparabilidad.\n- **Scores extremos:** indica si existen y por qué son una señal de cautela.\n- **Solapamiento:** destaca si el solapamiento es razonable; si es moderado, dilo como punto positivo.\n- **Variables a vigilar:** enumera las confusoras más fuertes y explica que se ajustará por ellas.\n\n**Lectura práctica:** resume qué aspectos son delicados y qué aspectos están bien para continuar."
}}

IMPORTANTE:
    - Incluye los valores numéricos reales devueltos por la herramienta (auc, cramers_v, etc.).
    - Destaca también los aspectos positivos del diagnóstico, no solo las alertas.
    - La justificación debe ser legible como Markdown: usa subtítulos breves y viñetas.
    - No inventes cifras ni escribas el JSON a mano fuera del código ejecutado.
    - La única salida válida debe generarse dentro de un bloque de código con print(json.dumps(...)).

Recuerda:
- Usa `Action: diagnostico_causal_df_tool` para iniciar.
- Una vez tengas el resultado, escribe el JSON final en tu `Final Answer`.

"""

def generar_prompt_interpretar_estimacion_causal(treatment_col: str, outcome_col: str, method: str) -> str:
    return f"""
Ejecuta una unica accion:
Action: estimate_causal_effect_tool
Action Input: {{}}

Contexto:
- Tratamiento: `{treatment_col}`.
- Resultado: `{outcome_col}`.
- Metodo: `{method}`.

La herramienta devuelve JSON con `estimate`, `intervalo_bajo`, `intervalo_alto`, `intervalo_incluye_cero`, `metodo` o `error`.

Despues de la observacion, responde directamente con `Final Answer:` y tres secciones:
1. **Magnitud del efecto**
2. **Intervalo de confianza**
3. **Conclusion**

Reglas:
- No llames ninguna otra herramienta.
- No escribas `Action: None`.
- No incluyas codigo, JSON ni detalles internos.
- No inventes resultados.
- Si hay `error`, explica que el metodo no produjo una estimacion fiable y sugiere probar otro metodo.
- Usa los valores numericos concretos redondeados a 2 decimales.
- Explica el signo del efecto: positivo aumenta `{outcome_col}`, negativo lo reduce.
- Si el intervalo no incluye 0, indica que el efecto es compatible con una asociacion causal positiva/negativa bajo los supuestos del DAG.
- Si el intervalo incluye 0, indica que hay incertidumbre y que no se puede descartar ausencia de efecto.
- Cierra con una advertencia breve: esto depende de la calidad del DAG, las variables de ajuste y el supuesto de no confusion no observada.
"""


def generar_prompt_validacion_robustez() -> str:
    return """
Ejecuta una unica accion:
Action: refute_estimate_tool
Action Input: {}

La herramienta devuelve JSON con `estimate`, `new_effect`, `cambio_absoluto`, `cambio_relativo`, `p_valor`, `refutacion` o `error`.

Despues de la observacion, responde directamente con `Final Answer:` y dos secciones:
1. **Resultado de la refutacion**
2. **Conclusion de robustez**

Reglas:
- No llames ninguna otra herramienta.
- No escribas `Action: None`.
- No incluyas codigo ni JSON.
- No inventes valores.
- Si hay `error`, explica que no se pudo validar la robustez.
- Usa `estimate`, `new_effect`, `cambio_absoluto`, `cambio_relativo` y `p_valor` si estan disponibles.
- Considera cambio pequeno si `cambio_relativo` es menor que 0.1.
- Si `p_valor` es alto, explica que la prueba no aporta evidencia fuerte contra el efecto estimado.
- Cierra con una advertencia breve: esta es una prueba de robustez, no una garantia definitiva de causalidad.
"""
