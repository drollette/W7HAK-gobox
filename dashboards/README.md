Place exported Grafana dashboard JSON files here.

## w7hak_telemetry_dashboard.json

Starter dashboard with four panels: LiFePO4 cell voltages, thermal sensors, system power draw, and solar input.

To use this dashboard:
1. Open your Grafana instance (e.g., `http://192.168.7.2:3000`).
2. Go to Dashboards -> Import.
3. Upload `w7hak_telemetry_dashboard.json` or paste its contents.
4. Select your local InfluxDB data source when prompted.