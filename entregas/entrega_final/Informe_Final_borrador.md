# Siniestralidad vial en Bogotá
## Informe final / Despliegue de Soluciones Analíticas
Estado: Borrador de trabajo


### 1. Contexto y pregunta de negocio

La siniestralidad vial representa un desafío para la seguridad y la movilidad de Bogotá, debido a sus consecuencias sobre la vida y la integridad de los ciudadanos. El proyecto busca estimar la cantidad mensual de siniestros viales con víctimas por localidad, con el propósito de apoyar el análisis territorial y la revisión de prioridades preventivas.

La pregunta de negocio planteada es: ¿Cuántos siniestros con víctimas se esperan el próximo mes en cada localidad y qué cambios frente al comportamiento histórico justifican una revisión de prioridades territoriales?. 

Para el análisis se considera 19 localidades de Bogotá, utilizando como unidad de estudio la combinación localidad-mes y un horizonte predictivo de un mes. Sumapaz se mantiene dentro de la descripción histórica, pero se excluye provisionalmente del modelado debido a su baja frecuencia de registros.

La fuente principal corresponde al conjunto de datos ACCIDENTE de la Secretaría Distrital de Movilidad, cuya caracterización ampliada comprende 906.664 registros y 23 columnas. Para la variable objetivo se consideran los siniestros clasificados como CON HERIDOS y CON MUERTOS, mientras que los registros de SOLO DAÑOS se excluyen por las discontinuidades identificadas en su registro. La solución busca complementar la información histórica mediante pronósticos que logran identificar variaciones esperadas entre localidades, estos resultados servirán como apoyo para la interpretación de prioridades territoriales, sin representar una medida directa de riesgo por habitante ni sustituir las decisiones de los especialistas.


### 2. Preparación de datos y selección de variables
Pendiente de consolidar las justificaciones metodológicas.

### 3. Modelos desarrollados y evaluación
Pendiente de incorporar la validación temporal actualizada y la comparación de hiperparámetros.

### 4. Análisis de errores por localidad
Pendiente de consolidar los resultados del modelo seleccionado.

### 5. Tablero, API y despliegue
Pendiente de integrar los avances de Andrés y Jairo.

### 6. Resultados y conclusiones
Pendiente de actualizar con los resultados definitivos.
