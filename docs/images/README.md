# Screenshots

These images are captured manually from the Airflow UI after a green run of
`ecommerce_pipeline`.

Green run used for capture:

```text
run_id: manual__2026-11-10T14:44:45+00:00
bronze_load            success
bronze_quality_gate    success
silver_rebuild         success
silver_quality_gate    success
gold_build             success
```

## Capture steps

1. Open <http://localhost:8080>.
2. Open **DAGs → ecommerce_pipeline**.
3. Capture the **Graph** view for the green run and save as
   `docs/images/airflow-graph.png`.
4. Switch to **Grid** view for the same run and save as
   `docs/images/airflow-grid.png`.
5. Open the **Logs** for `bronze_load` and save as
   `docs/images/airflow-logs-bronze.png`.
6. Open the **Logs** for `silver_quality_gate` and save as
   `docs/images/airflow-logs-silver-gate.png`.

Do not include secrets, connection passwords, or tokens in any screenshot.
