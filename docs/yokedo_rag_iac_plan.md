# 🧩 Plan Integrado RAG + IaC – Proyecto Yokedo
**Autor:** Pablo  
**Fecha:** Noviembre 2025  
**Versión:** 1.0  
**Estado:** En planificación  
**Duración estimada:** 12 semanas  

---

## 🎯 Objetivo General
Incorporar en Yokedo componentes reales de **Infrastructure as Code (IaC)** y **pipelines RAG (Retrieval-Augmented Generation)** que:
1. refuercen tu perfil profesional MLOps/LLMOps,  
2. funcionen de forma integrada con la arquitectura FastAPI + PostgreSQL + K3s, y  
3. aprovechen los campos de embeddings y logs ya presentes en el modelo de datos del MVP (`vector`, `semantic_similarity_log`, `user_affinities`).

---

## 🧱 Fase 1 – Infraestructura como Código (IaC básica)
**Duración:** Semanas 1 → 4  
**Objetivo:** desplegar la infraestructura base de microservicios Yokedo en K3s usando Terraform y/o Helm.

### Semana 1 – Base Kubernetes
- [ ] Revisar estructura de servicios (`auth-service`, `calendar-service`, `db-service`).  
- [ ] Crear manifests YAML parametrizados para cada servicio.  
- [ ] Probar despliegue manual con `kubectl apply -f`.

### Semana 2 – Terraform init
- [ ] Instalar y configurar Terraform localmente.  
- [ ] Crear módulo `infra/` con:
  - `main.tf`, `variables.tf`, `outputs.tf`  
  - definición de namespace `yokedo`  
  - creación automática de Secrets y ConfigMaps.  
- [ ] Validar plan con `terraform plan` y aplicar en K3s.

### Semana 3 – CI/CD infra
- [ ] Añadir workflow GitHub Actions que valide Terraform (`fmt`, `validate`, `plan`).  
- [ ] Integrar Terraform en pipeline de despliegue local.  
- [ ] Añadir outputs legibles (IPs, ports, secrets).

### Semana 4 – Documentación
- [ ] Crear `infra/README.md` con pasos de despliegue.  
- [ ] Añadir diagrama IaC (`PlantUML` o `diagrams.net`).

---

## 🧠 Fase 2 – Microservicio AI (Embeddings + Tokenización)
**Duración:** Semanas 5 → 8  
**Objetivo:** crear microservicio independiente `ai-service` que genere y consulte embeddings textuales.

### Semana 5 – Servicio básico
- [ ] Crear `backend/ai-service/` con FastAPI + Uvicorn.  
- [ ] Endpoint `/embed-text` → recibe texto, devuelve vector.  
- [ ] Modelo: `sentence-transformers` (`all-MiniLM-L6-v2`) o OpenAI embeddings.  
- [ ] Guardar vectores en PostgreSQL (`vector` extension).

### Semana 6 – Tokenización + cost tracking
- [ ] Usar `tiktoken` para contar tokens.  
- [ ] Registrar métricas: nº tokens, latencia, coste aprox.  
- [ ] Loggear en `user_interaction_logs`.

### Semana 7 – Búsqueda semántica
- [ ] Implementar FAISS o ChromaDB.  
- [ ] Endpoint `/semantic-search` → texto → coincidencias.  
- [ ] Aplicación real: encontrar usuarios con intereses o planes similares.

### Semana 8 – Observabilidad
- [ ] Añadir logs estructurados (JSON).  
- [ ] Endpoint `/health` con prometheus metrics.  
- [ ] Documentar en `ai-service/README.md`.

---

## 🧩 Fase 3 – Pipeline RAG Integrado
**Duración:** Semanas 9 → 12  
**Objetivo:** construir pipeline RAG completo y conectarlo con los datos de Yokedo.

### Semana 9 – Diseño de pipeline
- [ ] Etapas: _ingestión → chunking → embeddings → almacenamiento → retrieval → generación_.  
- [ ] Dataset: descripciones de planes (`availabilities.plan_text`).  
- [ ] Framework: LangChain o LlamaIndex.

### Semana 10 – Implementación local
- [ ] Prototipo RAG: responder a consultas tipo  
  “¿Qué actividades suelen hacer mis contactos los viernes?”  
- [ ] Guardar resultados y scores en `semantic_similarity_log`.

### Semana 11 – Integración backend
- [ ] Endpoint `/ai/ask` → consulta al pipeline.  
- [ ] Guardrails básicos (filtro de prompt).  
- [ ] Integración con `notifications` para sugerencias automáticas.

### Semana 12 – IaC avanzada + CI/CD
- [ ] Añadir `ai-service` al Terraform.  
- [ ] Variables CPU/memoria + Secrets API Keys.  
- [ ] Workflow GitHub Actions para test + lint + deploy.  
- [ ] Actualizar `README` con diagrama del pipeline.

---

## ✅ Resultados Esperados
- [ ] IaC reproducible con Terraform (K3s).  
- [ ] Microservicio AI funcional con embeddings y tokenización.  
- [ ] Pipeline RAG completo documentado.  
- [ ] Integración real con tablas PostgreSQL existentes.  
- [ ] Logs + métricas para observabilidad.  
- [ ] README + diagramas listos para portfolio y entrevistas.

---

## 🧠 Competencias que demuestra
| Área | Habilidad | Evidencia en Yokedo |
|------|------------|---------------------|
| **MLOps** | CI/CD, versionado, testing | Workflows GitHub Actions |
| **IaC** | Terraform, Helm, K3s automation | `infra/` y despliegue reproducible |
| **LLMOps** | RAG pipeline + tokenización + embeddings | `ai-service` integrado |
| **Data Engineering** | PostgreSQL + FAISS + logs | `vector`, `semantic_similarity_log` |
| **Security by Design** | Secrets, auth, políticas mínimas en Terraform | configuración K8s |

---

## 📦 Archivos que se crearán
```
/backend/ai-service/
│   ├── app/main.py
│   ├── app/routers/
│   ├── app/models/
│   ├── requirements.txt
│   └── README.md
/infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── README.md
/docs/
│   └── yokedo_rag_iac_plan.md  ← este documento
```

---

## 🔄 Seguimiento
- [ ] Fase 1 – IaC básica
- [ ] Fase 2 – AI Embeddings + Tokenización
- [ ] Fase 3 – RAG completo + CI/CD  
*(actualiza cada checkbox en el diario .md diario de Yokedo)*

---

> **Nota:** Este plan está diseñado para integrarse gradualmente con la infraestructura y modelo de datos actuales (`yokedo_data_schema.md`).  
> La inserción de embeddings usa el tipo `vector`, y los logs RAG se guardan en `semantic_similarity_log`.
