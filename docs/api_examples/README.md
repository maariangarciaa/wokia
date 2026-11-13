# Ejemplos Postman

Estos JSON estan pensados para probar el flujo causal completo con:

```text
ElectricCarData_Clean.csv
```

Base URL:

```text
http://localhost:8000
```

Orden recomendado:

1. `01_causal_candidates.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/candidates`

2. `02_causal_hypotheses.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/hypotheses`

3. `03_causal_treatment.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/treatment`

4. `04_causal_dag.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/dag`

5. `05_causal_identify.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/identify`

6. `06_causal_method.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/method`

7. `07_causal_estimate.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/estimate`

8. `08_causal_refute.json`
   `POST /datasets/ElectricCarData_Clean.csv/causal/refute`

Nota: los ejemplos 5, 7 y 8 incluyen un DAG completo ya generado para que puedas probarlos directamente.
