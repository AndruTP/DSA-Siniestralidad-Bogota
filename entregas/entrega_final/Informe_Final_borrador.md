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

Las evaluaciones con ventanas expansivas evidenciaron variaciones importantes entre años, especialmente en el ensamble con inicio en 2019, que presentó un deterioro frente a la referencia durante 2022 y 2023. Para ampliar este análisis, se compararon cuatro configuraciones de hiperparámetros con diferentes ventanas de entrenamiento, identificando que la alternativa de menor complejidad redujo el error respecto al ensamble original, aunque no superó la referencia histórica en el promedio de ambos años. Continúa pendiente conciliar las diferencias entre las métricas del notebook y MLflow, así como definir y documentar la selección definitiva del modelo antes de realizar la evaluación final de 2025.

#### Ajuste de hiperparámetros y validación temporal

Para complementar la evaluación inicial se compararon cuatro configuraciones de hiperparámetros del ensamble relativo, considerando diferentes niveles de complejidad, flexibilidad y regularización. Se utilizaron ventanas de entrenamiento con inicio en 2017 y 2019, evaluando los resultados de 2022 y 2023 mediante un procedimiento temporal expansivo. En total se realizaron 16 ajustes exploratorios, correspondientes a cuatro configuraciones, dos ventanas de inicio y dos años de evaluación. La comparación se efectuó utilizando el MAE y la mejora porcentual frente a la media móvil de 12 meses.

#### Resultados de la comparación 2022-2023

| Configuración | Inicio | MAE modelo | MAE referencia | Mejora |
|---|---:|---:|---:|---:|
| Menor complejidad | 2017 | 6,8607 | 6,8088 | -0,76 % |
| Mayor regularización | 2017 | 6,8974 | 6,8088 | -1,30 % |
| Original | 2017 | 6,9878 | 6,8088 | -2,63 % |
| Mayor flexibilidad | 2017 | 7,0406 | 6,8088 | -3,40 % |
| Menor complejidad | 2019 | 8,8277 | 6,8088 | -29,65 % |

La configuración de menor complejidad con entrenamiento desde 2017 obtuvo el menor MAE promedio entre las alternativas evaluadas, alcanzando 6,8607 frente a 6,8088 de la referencia. Aunque representa una mejora respecto a la configuración original del ensamble, no logró superar el comportamiento de la media móvil de 12 meses en el promedio de ambos años, al revisar los resultados individualmente se observa que esta configuración presentó una mejora del 0,29 % durante 2022, mientras que en 2023 registró un deterioro del 1,78 %. Esto evidencia que la reducción de complejidad favoreció el desempeño respecto al ensamble original, pero no garantizó una ventaja sostenida frente a la referencia histórica.

#### Interpretación y selección del modelo

Los experimentos muestran que el desempeño de los ensambles depende tanto de los hiperparámetros como de la ventana de entrenamiento utilizada. La configuración seleccionada inicialmente por su resultado de 2024 no demuestra superioridad consistente al considerar los años anteriores, porr lo tanto la media móvil de 12 meses continúa siendo una referencia competitiva y no se cuenta todavía con evidencia suficiente para adoptar el ensamble como modelo operativo definitivo.

La comparación realizada es exploratoria y requiere complementar su trazabilidad experimental en MLflow. La evaluación final de 2025 permanece reservada hasta establecer y documentar la selección definitiva del modelo.

### 4. Análisis de errores por localidad
Se realizó un análisis territorial del ensamble relativo entrenado con datos de 2019 a 2023, utilizando las 228 observaciones correspondientes a la validación de 2024. Se calcularon el error absoluto medio (MAE), el sesgo de las predicciones y el porcentaje de mejora frente a la media móvil de 12 meses para las 19 localidades consideradas. Los resultados muestran que el modelo supera la referencia histórica en 13 localidades, mientras que en las otras 6 presenta un mayor error, lo que evidencia diferencias en su capacidad predictiva según el territorio.

#### Resultados territoriales destacados

| Localidad | MAE modelo | MAE referencia | Mejora |
|---|---:|---:|---:|
| Kennedy | 16,2184 | 15,7639 | -2,88 % |
| Suba | 8,8746 | 12,6528 | +29,86 % |
| Fontibón | 9,2064 | 11,2083 | +17,86 % |
| Puente Aranda | 9,1913 | 10,2500 | +10,33 % |
| Engativá | 7,5147 | 8,0139 | +6,23 % |
| Santa Fe | 7,1945 | 5,8403 | -23,19 % |
| Tunjuelito | 6,5285 | 4,9653 | -31,48 % |

Kennedy presenta el mayor error absoluto medio del modelo, con 16,2184 siniestros por localidad-mes, superando el error de la referencia. Por el contrario, Suba registra una reducción del 29,86 % y Fontibón del 17,86 %, mostrando un mejor comportamiento predictivo respecto a sus promedios históricos, asi mismo se identificaron diferencias en el sesgo de las predicciones en donde Engativá presenta un sesgo positivo de 4,1767, lo que indica una tendencia a sobreestimar los siniestros, mientras que Usaquén registra un sesgo de -4,1654, reflejando una tendencia a subestimarlos.

#### Interpretación de los resultados

Aunque el ensamble alcanza una mejora global del 4,4846 % frente a la referencia, su desempeño no es uniforme entre localidades. Por esta razón, los resultados deben interpretarse considerando tanto el error global como las diferencias territoriales, en localidades donde el modelo presenta mayores errores que la referencia, como Kennedy, Santa Fe y Tunjuelito, sus predicciones requieren especial precaución antes de orientar una revisión de prioridades. Estos resultados permiten identificar dónde el modelo ofrece una estimación más precisa y dónde se requiere fortalecer su evaluación. Sin embargo, no constituyen por sí solos una medida de riesgo vial ni justifican automáticamente cambios en la asignación de recursos.

El análisis corresponde exclusivamente a la validación de 2024 y debe complementarse con la evaluación de estabilidad temporal antes de establecer el modelo definitivo.

### 5. Tablero, API y despliegue
Pendiente de integrar los avances de Andrés y Jairo.

### 6. Resultados y conclusiones
Pendiente de actualizar con los resultados definitivos.
