# Yokedo

Yokedo es una web app para coordinar quedadas entre amigos, permitiendo compartir disponibilidad, generar enlaces de invitación y proponer planes en un par de clics.

## Estructura del repositorio

- `backend/auth-service/`: servicio de autenticación (FastAPI).  
- `.github/workflows/`: configuración de CI/CD.  
- `docker-compose.yml`: PostgreSQL + servicios en local.  
- `README.md`: este documento.

## Primeros pasos

1. Clonar el repo  
2. `docker-compose up --build`  
3. Explorar el servicio de auth en `http://localhost:8001`



## 📘 Documentación Técnica

- [Modelo de Datos (v1.0)](docs/data/yokedo_data_schema.md)
- [MER (PlantUML)](docs/diagrams/yokedo_mer.puml)
- [Arquitectura General](docs/architecture/system_overview.md)
- [Decisiones de Diseño (ADR)](docs/decisions/)


![MER de Yokedo](docs/diagrams/yokedo_mer.png)

