# Home Assistant - Integración Aigües de l'Horta

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]][license]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

<!-- Opcional: Añadir badges de estado si tienes CI/CD -->
<!-- [![CI Status](...)] -->

<!-- Opcional: Añadir una imagen/screenshot -->
<!-- ![Screenshot de la integración en Home Assistant](URL_A_TU_IMAGEN.png) -->

Integración personalizada para Home Assistant que permite monitorizar el consumo de agua y la lectura del contador del servicio [Aigües de l'Horta](https://www.aigueshorta.es).

**Esta integración utiliza web scraping y llamadas directas a la API interna del portal de clientes, por lo que puede dejar de funcionar si el sitio web de Aigües de l'Horta sufre cambios significativos.**

## Funcionalidades

*   Obtiene la **lectura actual del contador** de agua.
*   Obtiene el **consumo horario** de agua de las últimas horas/días.
*   Crea entidades de sensor en Home Assistant para:
    *   Lectura total del contador (`sensor.aigues_de_l_horta_TUNOMBRE_meter_reading`).
    *   Consumo de la última hora registrada (`sensor.aigues_de_l_horta_TUNOMBRE_hourly_consumption`).
*   Muestra información adicional como atributos (número de contrato, dirección, historial horario).

## Instalación

### Método 1: Instalación Manual

1.  Descarga la última [release](https://github.com/sercasan/hass-aigues-horta/releases) de este repositorio.
2.  Descomprime el archivo descargado.
3.  Copia la carpeta `custom_components/aigues_horta` (que contiene todos los archivos `.py`, `manifest.json`, etc.) dentro de la carpeta `custom_components` de tu instalación de Home Assistant. Si la carpeta `custom_components` no existe, créala dentro de tu directorio principal de configuración (`/config`).
    *   La estructura final debería ser: `/config/custom_components/aigues_horta/__init__.py`, `/config/custom_components/aigues_horta/sensor.py`, etc.
4.  Reinicia Home Assistant.

## Configuración

Una vez instalada la integración (y después de reiniciar si fue necesario):

1.  Ve a `Configuración` > `Dispositivos y Servicios` en tu Home Assistant.
2.  Haz clic en el botón `+ AÑADIR INTEGRACIÓN` en la esquina inferior derecha.
3.  Busca "Aigües de l'Horta".
4.  Selecciona la integración. Aparecerá un cuadro de diálogo pidiendo tus credenciales.
5.  Introduce el **Email o Usuario** y la **Contraseña** que usas para acceder al portal web de [Aigües de l'Horta](https://www.aigueshorta.es/login).
6.  Haz clic en `ENVIAR`.
7.  La integración intentará iniciar sesión y, si tiene éxito, se añadirá a Home Assistant. Se creará automáticamente un dispositivo y las entidades correspondientes.

## Entidades Creadas

Se crearán las siguientes entidades (donde `TUNOMBRE` será reemplazado por tu usuario o un identificador único):

*   **`sensor.aigues_de_l_horta_TUNOMBRE_meter_reading`**:
    *   **Estado:** La última lectura total registrada por el contador (en m³).
    *   **Atributos:** Número de contrato, dirección, fecha de la última lectura.
*   **`sensor.aigues_de_l_horta_TUNOMBRE_hourly_consumption`**:
    *   **Estado:** El consumo de agua durante la última hora registrada (en m³).
    *   **Atributos:** Número de contrato, dirección, historial de consumo horario (`hourly_consumption_history`), hora de la última actualización horaria (`last_updated_hour`).

## Uso en el Panel de Energía

Puedes usar el sensor `sensor.aigues_de_l_horta_TUNOMBRE_hourly_consumption` en el [Panel de Energía](https://www.home-assistant.io/docs/energy/) de Home Assistant para visualizar tu consumo de agua horario.

1.  Ve a `Configuración` > `Paneles` > `Energía`.
2.  En la sección "Consumo de agua", haz clic en `AÑADIR CONSUMO`.
3.  Selecciona la entidad `sensor.aigues_de_l_horta_TUNOMBRE_hourly_consumption`.
4.  Asegúrate de marcar la opción "Usar una entidad que rastree el consumo total". **Aunque nuestro sensor es horario, su `state_class: TOTAL` y el atributo `last_reset` permiten a HA interpretarlo correctamente para gráficos de consumo por hora.**
5.  Guarda la configuración.

Los datos empezarán a aparecer en el gráfico del panel de energía.

## Solución de Problemas

*   **Error de Autenticación / 401 Unauthorized:**
    *   Verifica que tu usuario y contraseña son correctos. Intenta iniciar sesión manualmente en la web.
    *   La web de Aigües de l'Horta podría haber cambiado su sistema de login o API. Revisa los [problemas (issues)](https://github.com/sercasan/hass-aigues-horta/issues) del repositorio por si alguien más lo ha reportado o crea uno nuevo.
*   **Sensores no disponibles o con valor `unknown`:**
    *   Revisa los registros de Home Assistant (`Configuración` > `Sistema` > `Registros` > `Cargar registros completos`) y busca errores relacionados con `custom_components.aigues_horta`.
    *   El error puede indicar un problema al contactar la API, parsear la respuesta, o un cambio en la estructura de la web.
    *   Asegúrate de que tu Home Assistant tiene conexión a internet.
*   **Datos Retrasados:** La integración actualiza los datos cada hora (por defecto). Los datos mostrados dependen de cuándo Aigües de l'Horta publica la información en su web/API, por lo que puede haber un pequeño retraso respecto al tiempo real.

## Contribuciones

Las contribuciones son bienvenidas. Si encuentras errores, tienes sugerencias o quieres mejorar la integración, por favor:

1.  Revisa los [problemas abiertos](https://github.com/sercasan/hass-aigues-horta/issues).
2.  Crea un [nuevo problema](https://github.com/sercasan/hass-aigues-horta/issues/new) para describir el bug o la mejora.
3.  Si quieres contribuir con código, haz un fork del repositorio, crea una rama para tus cambios y envía una Pull Request.

## Descargo de Responsabilidad

Esta es una integración no oficial creada por la comunidad y no está afiliada ni soportada por Aigües de l'Horta. Úsala bajo tu propio riesgo. Cambios en el sitio web oficial pueden romper esta integración sin previo aviso.

[releases]: https://github.com/sercasan/hass-aigues-horta/releases
[releases-shield]: https://img.shields.io/github/release/sercasan/hass-aigues-horta.svg?style=for-the-badge
[license]: https://github.com/sercasan/hass-aigues-horta/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/sercasan/hass-aigues-horta.svg?style=for-the-badge
