"""
Trains and registers the traditional, predictive models (demand forecast,
pricing sensitivity, segmentation) used by the Buyer and Collection Planner
persona, tracked end to end with MLflow.

LESSON LEARNED (reused from earlier case studies): on Databricks Free
Edition, MLflow returns a persistent CONFIG_NOT_AVAILABLE error from roughly
the third call to mlflow.start_run() within the same session. A fresh UUID4
is generated for every run name to work around this rather than relying on
MLflow's own auto-incrementing run naming.
"""

import os
import uuid

import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/atelier/demand_forecast")


def load_training_data() -> pd.DataFrame:
    # Replace with a real read from atelier.gold.sales_history joined with
    # atelier.gold.trends, via databricks-sql-connector.
    return pd.DataFrame()


def train_demand_model(df: pd.DataFrame):
    run_name = f"demand-forecast-{uuid.uuid4()}"
    with mlflow.start_run(run_name=run_name):
        features = df.drop(columns=["units_sold"])
        target = df["units_sold"]
        x_train, x_test, y_train, y_test = train_test_split(features, target, test_size=0.2)

        model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
        model.fit(x_train, y_train)
        score = model.score(x_test, y_test)

        mlflow.log_param("n_estimators", 200)
        mlflow.log_param("max_depth", 8)
        mlflow.log_metric("r2_score", score)
        mlflow.sklearn.log_model(model, artifact_path="model")

        mlflow.register_model(
            model_uri=f"runs:/{mlflow.active_run().info.run_id}/model",
            name="atelier.gold.demand_forecast_model",
        )


if __name__ == "__main__":
    training_data = load_training_data()
    if not training_data.empty:
        train_demand_model(training_data)
