# MQTT Thermal Printer API

This repository provides a lightweight service to print dynamic content to a thermal receipt printer via **MQTT**.  
The system is designed for automation and smart home integrations, enabling tasks such as printing weather updates, news headlines, or jokes directly from API endpoints.

---

## System Overview

1. **Content Sources**  
   - Each source retrieves structured text (e.g., weather, news, jokes).  
   - Sources implement a unified interface `get_text()` returning a title and text lines.  

2. **Rendering & Conversion**  
   - Text is rendered into a monochrome PNG image.  
   - The image is base64-encoded for transport.  

3. **Transport via MQTT**  
   - The payload is wrapped in JSON:  
     ```json
     {
       "data_type": "png",
       "data_base64": "<encoded image>"
     }
     ```  
   - Published to a configured MQTT topic with QoS 2.  

4. **Printer**  
   - The printer subscribes to the topic and prints the decoded PNG.  
   - **Note:** This printer does not use ESC/POS. It expects PNG images wrapped in JSON.  

---

## API Endpoints

The FastAPI application exposes endpoints to trigger print jobs. Examples:

- `GET /print/weather` → Prints current weather in Unterseen.  
- `GET /print/news` → Prints a random news headline.  
- `GET /print/fun` → Prints a joke or fact.  

Each endpoint:  
1. Fetches and formats data from its source.  
2. Renders the text as an image.  
3. Publishes the print job via MQTT.  

---

## Configuration

The service is configured via environment variables.  

### Example `.env` file (template):

```ini
# Authentication
API_KEY=<YOUR_API_KEY>
UI_PASS=<YOUR_UI_PASSWORD>

# MQTT broker
MQTT_HOST=<BROKER_HOST>
MQTT_PORT=8883
MQTT_TLS=true
MQTT_USERNAME=<BROKER_USERNAME>
MQTT_PASSWORD=<BROKER_PASSWORD>
PRINT_TOPIC=<PRINTER_TOPIC>
PRINT_QOS=2

# Print image settings
PRINT_QUEUE_DIR=/data/print-queue
GRAYSCALE_PNG=false
PRINT_BRIGHTNESS=1.0
PRINT_CONTRAST=1.0
PRINT_DITHER=floyd
PRINT_GAMMA=1.0
PRINT_THRESHOLD=128

# Sources
NEWSAPI_KEY=<YOUR_NEWSAPI_KEY>
NEWS_COUNTRY=US
