# Siniestralidad vial en Bogotá
## Informe final / Despliegue de Soluciones Analíticas
Estado: Borrador de trabajo


### 1. Contexto y pregunta de negocio

La siniestralidad vial representa un desafío para la seguridad y la movilidad de Bogotá, debido a sus consecuencias sobre la vida y la integridad de los ciudadanos. El proyecto busca estimar la cantidad mensual de siniestros viales con víctimas por localidad, con el propósito de apoyar el análisis territorial y la revisión de prioridades preventivas.

La pregunta de negocio planteada es: ¿Cuántos siniestros con víctimas se esperan el próximo mes en cada localidad y qué cambios frente al comportamiento histórico justifican una revisión de prioridades territoriales?. 

Para el análisis se considera 19 localidades de Bogotá, utilizando como unidad de estudio la combinación localidad-mes y un horizonte predictivo de un mes. Sumapaz se mantiene dentro de la descripción histórica, pero se excluye provisionalmente del modelado debido a su baja frecuencia de registros.

La fuente principal corresponde al conjunto de datos ACCIDENTE de la Secretaría Distrital de Movilidad, cuya caracterización ampliada comprende 906.664 registros y 23 columnas. Para la variable objetivo se consideran los siniestros clasificados como CON HERIDOS y CON MUERTOS, mientras que los registros de SOLO DAÑOS se excluyen por las discontinuidades identificadas en su registro. La solución busca complementar la información histórica mediante pronósticos que logran identificar variaciones esperadas entre localidades, estos resultados servirán como apoyo para la interpretación de prioridades territoriales, sin representar una medida directa de riesgo por habitante ni sustituir las decisiones de los especialistas.


### 2. Preparación de datos y selección de variables

La preparación de los datos se realizó a partir del conjunto ACCIDENTE de la Secretaría Distrital de Movilidad, organizando los registros de siniestros con víctimas por localidad y mes. Se construyó un panel temporal con 19 localidades, considerando los periodos disponibles entre 2016 y 2025. Después de generar las variables históricas y exigir 12 meses de información previa, se obtuvieron 2.052 observaciones correspondientes al periodo 2017-2025.

Para el entrenamiento inicial se utilizaron los registros de 2017 a 2023, mientras que 2024 se reservó para la validación de los modelos y 2025 para la evaluación final. Esta separación temporal permite evaluar las predicciones respetando el orden cronológico de los datos y evitando utilizar información futura durante el entrenamiento.

#### Selección y construcción de variables

Las variables se organizaron en diferentes grupos, teniendo en cuenta su relación con el comportamiento histórico de los siniestros:

**Variables territoriales:** la localidad permite identificar las diferencias en los niveles de siniestralidad entre zonas de Bogotá.

**Variables temporales:** el mes, el año y las transformaciones cíclicas del mes permiten representar patrones de calendario y estacionalidad.

**Variables históricas:** los rezagos de 1, 3, 6 y 12 meses permiten incorporar los registros anteriores de cada localidad.

**Medias móviles:** los promedios de 3, 6 y 12 meses permiten representar tendencias recientes y de mayor duración.

**Indicador 2020-2021:** permite identificar el periodo asociado a las alteraciones de movilidad durante la pandemia.

Asi mismo se evaluaron variables derivadas como la media móvil exponencial de seis meses y un índice de estacionalidad de la ciudad. En los modelos relativos, algunos indicadores históricos se transformaron respecto a la media móvil de 12 meses, buscando representar las variaciones frente al comportamiento habitual de cada localidad.

Las variables históricas se calcularon utilizando información de meses anteriores al periodo que se desea predecir. La selección de características respondió inicialmente a criterios temporales y a su capacidad para representar tendencias, estacionalidad y diferencias territoriales, mientras que su utilidad predictiva debe contrastarse mediante la evaluación temporal de los modelos.

### 3. Modelos desarrollados y evaluación

Se desarrollaron los diferentes modelos supervisados para estimar el número mensual de siniestros viales con víctimas por localidad, considerando alternativas basadas en Gradient Boosting con pérdida Poisson, regresión binomial negativa (NB2) y modelos relativos con ajuste respecto a la media móvil de 12 meses.

La evaluación inicial se realizó mediante una partición temporal, utilizando los datos de entrenamiento hasta 2023 y reservando 2024 para la validación. La comparación se efectuó frente a una referencia basada en la media móvil de 12 meses, utilizando principalmente el error absoluto medio (MAE), complementado con RMSE y sesgo.

#### Resultados de validación de 2024

| Modelo | MAE | RMSE |
|---|---:|---:|
| Media móvil de 12 meses | 7,0146 | 9,5464 |
| HGB Poisson 2017-2023 | 7,1921 | 10,1549 |
| NB2 revisada 2017-2023 | 7,3664 | 9,9919 |
| Ensamble relativo 2019-2023 | 6,7000 | 9,3664 |
| Ensamble relativo 2021-2023 | 6,7931 | 9,3401 |

El ensamble relativo entrenado con datos de 2019 a 2023 presentó el menor MAE entre las configuraciones comparadas, alcanzando una mejora del 4,4846 % frente a la referencia. Sin embargo, este resultado no cumple la meta inicial de reducir el error en al menos un 10 %.

#### Estabilidad temporal y aspectos pendientes

Las evaluaciones con ventanas expansivas evidenciaron variaciones importantes entre años, de forma particular el ensamble con inicio en 2019 presentó un deterioro frente a la referencia durante 2022 y 2023, lo que limita su selección a partir del resultado favorable obtenido en 2024, adicionalmente, se identificaron diferencias entre las métricas registradas en el notebook y una ejecución de MLflow. Por lo tanto, se requiere conciliar estos resultados, ampliar la comparación temporal de configuraciones y justificar los hiperparámetros antes de establecer el modelo definitivo, por lo cual la evaluación final sobre 2025 permanece reservada hasta completar y congelar el procedimiento de selección del modelo.

### 4. Análisis de errores por localidad
Pendiente de consolidar los resultados del modelo seleccionado.

### 5. Tablero, API y despliegue
Pendiente de integrar los avances de Andrés y Jairo.

### 6. Resultados y conclusiones
Pendiente de actualizar con los resultados definitivos.
