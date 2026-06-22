from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import mlflow
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
    import pandas as pd


@workflow.defn
class TrainingWorkflow:
    @workflow.run
    async def run(self, config: dict) -> dict:
        dataset_path = config["dataset_path"]
        target = config["target_column"]
        problem_type = config["problem_type"]
        model_type = config.get("model_type", "random_forest")
        params = config.get("params", {})

        df = pd.read_csv(dataset_path)
        X = df.drop(columns=[target])
        y = df[target]

        # Simple train-test split
        split = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        if problem_type == "classification":
            if model_type == "logistic_regression":
                model = LogisticRegression(**params)
            else:
                model = RandomForestClassifier(**params)
        else:
            if model_type == "linear_regression":
                model = LinearRegression(**params)
            else:
                model = RandomForestRegressor(**params)

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {}
        if problem_type == "classification":
            metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        else:
            metrics["mse"] = float(mean_squared_error(y_test, y_pred))
            metrics["r2"] = float(r2_score(y_test, y_pred))

        mlflow.set_tracking_uri("http://mlflow:5000")
        with mlflow.start_run(run_name=config.get("run_name", "workflow_run")):
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(model, "model")

        return {"metrics": metrics, "status": "completed", "model_type": model_type}
