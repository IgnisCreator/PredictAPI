Instrucciones para el agente de IA en este proyecto. Si una instrucción del usuario contradice este archivo, gana el usuario, pero avísale del conflicto.

## 1. Contexto
PredictAPI: API REST que sirve predicciones de riesgo crediticio (dataset German Credit) y explica cada una con SHAP. Proyecto 2 del portafolio; el alcance vive en `docs/backlog.md`.

Stack: Python 3.12 (gestionado con uv), scikit-learn, SHAP, FastAPI + Pydantic, PostgreSQL (registro de predicciones), Docker, GitHub Actions. Nada de frontend propio: la interfaz es Swagger/OpenAPI que genera FastAPI.

El usuario puede no ser programador. Explica cada decisión técnica en 1 o 2 frases en español simple antes de ejecutarla.

## 2. Idioma
- Responde siempre en español; explica la jerga la primera vez que aparece.
- Código, nombres de archivos, variables, endpoints y columnas en inglés (snake_case en Python y SQL).
- README y model card en inglés (requisito del portafolio), con versión en español del README.
- Comentarios en el código solo cuando no es obvio, en español.

## 3. Reglas de ML (no negociables)
- Partición train/test estratificada con semilla fija. El test se usa una sola vez, al final; la selección de modelo se hace con validación cruzada sobre train.
- Toda transformación (escalado, one-hot) vive dentro del `Pipeline` de sklearn, para que nunca se ajuste con datos de test.
- Siempre comparar contra un baseline (`DummyClassifier`).
- Cada artefacto de modelo queda registrado en `models/manifest.json` con su hash SHA-256, schema de features, métricas, hash del dataset y versiones de librerías. La API se niega a cargar un artefacto cuyo hash no coincida.
- No inventar métricas: todo número del README sale de una ejecución real registrada en `docs/validation.md`.

## 4. Estructura
```
app/          API FastAPI (aparece en PA-02)
training/     scripts de entrenamiento
models/       artefactos versionados + manifest.json
tests/        pytest
docs/         backlog.md, decisions.md, validation.md
data/         caché del dataset (ignorado por git)
```
Menos archivos es mejor. No crear capas ni abstracciones hasta que una segunda implementación las necesite.

## 5. Flujo de trabajo
- Una fase del backlog por rama (`feature/pa-01-datos-baseline`). Commit en español y descriptivo por cada parte que funcione.
- Una fase se marca `validated` solo con evidencia (comando ejecutado + resultado) en `docs/validation.md`.
- Si algo falla, lee el error completo antes de cambiar código. Máximo 3 intentos por error; luego detente y resume.
- No agregues funcionalidades que no estén en el backlog sin preguntar.

## 6. Git y secretos
- Nunca `git push --force`, `git reset --hard` ni borrar `.git` sin confirmación explícita.
- Secretos solo en `.env` (ignorado); `.env.example` sin valores reales.
- Sin datos personales reales: German Credit es un dataset público y anonimizado.
