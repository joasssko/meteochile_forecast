# MeteoChile Forecast Integration for Home Assistant

![HACS Valid](https://img.shields.io/badge/HACS-Custom-orange.svg)

Esta es una integración personalizada (Custom Integration) para Home Assistant que crea una entidad de clima (`weather`) con el pronóstico para los siguientes 3 a 5 días, utilizando los datos oficiales proporcionados por la Dirección Meteorológica de Chile (MeteoChile).

## Características

- Entidad de Clima (`weather`) nativa de Home Assistant.
- Pronóstico diario para 3 a 5 días (temperaturas máximas, mínimas, estado del clima y descripción detallada).
- Mapeo inteligente del estado del tiempo basado en la prioridad del clima del día.
- **Sin necesidad de claves de API**: obtiene los datos del archivo de pronóstico público oficial.
- Permite configurar múltiples ciudades.
- Selección interactiva de la ciudad en la lista desplegable durante la instalación.

## Instalación a través de HACS

Esta integración es compatible con HACS (Home Assistant Community Store).

1. Ve a HACS en tu panel de Home Assistant.
2. Selecciona **Integraciones**.
3. Haz clic en los tres puntos (menú) en la esquina superior derecha y selecciona **Repositorios Personalizados (Custom repositories)**.
4. Agrega la URL de este repositorio (`https://github.com/joasssko/meteochile_forecast`) y selecciona la categoría **Integration**.
5. Haz clic en **Agregar**.
6. Busca "MeteoChile Weather" (o "Pronóstico del tiempo en Chile") en HACS y dale a **Descargar**.
7. ¡Reinicia tu Home Assistant!

## Configuración

Una vez instalada la integración y reiniciado Home Assistant:

1. Ve a **Ajustes** > **Dispositivos y Servicios** > **Añadir Integración**.
2. Busca **MeteoChile Weather**.
3. Selecciona tu **Ciudad** en la lista desplegable de ciudades.
4. ¡Listo! Se creará la entidad de clima correspondiente a la ciudad seleccionada con el pronóstico diario.

Puedes repetir este proceso para agregar tantas ciudades de Chile como desees.
