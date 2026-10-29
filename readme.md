# Práctica Final - Fase 1: Adquisición, Preprocesado y Transformación

## Descripción del Proyecto
Este proyecto implementa un pipeline en Python para la adquisición, preprocesamiento y transformación de datasets numismáticos procedentes de dos fuentes (Ibercoin y Biddr). El objetivo es unificar los registros con un formato JSON, normalizando los precios a Euros (€), traduciendo o normalizando campos cuando es necesario, y aplicando una limpieza estricta para eliminar nulos o campos vacíos.

## Estructura del Directorio
La arquitectura del proyecto sigue unos estándares de ingeniería de software (alta cohesión y bajo acoplamiento):

Practica_final_chat_bots/
│
├── data/
│   ├── raw/               # Archivos en crudo obtenidos en la fase de adquisición (HTML)
│   └── processed/         # Datasets en JSON, por separado y el final
│
├── src/
│   ├── configuracion/     # Configuración global y constantes
│   ├── parsers/           # Parsers específicos para cada fuente de datos (Ibercoin y Biddr)
│   ├── scrapers/          # Scripts de extracción y control de peticiones
│   ├── utils/             # Funciones de ayuda y gestión de almacenamiento
│   └── preprocess.py      # Script principal del pipeline de transformación y limpieza
│
├── requirements.txt       # Dependencias del proyecto
└── readme.md              # Documentación de la práctica