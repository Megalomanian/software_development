export type NodeType =
  | "data_source"
  | "feature_engineering"
  | "model_training"
  | "evaluation";

export interface NodeConfig {
  // data_source
  dataset_id?: string;

  // feature_engineering
  operations?: FeatureOp[];

  // model_training
  model_type?: "random_forest" | "logistic_regression" | "linear_regression" | "xgboost";
  params?: Record<string, string | number>;

  // evaluation
  metrics?: string[];
}

export interface FeatureOp {
  type: "drop_columns" | "fill_na" | "normalize" | "one_hot_encode" | "label_encode";
  column?: string;
  value?: string;
}

export const NODE_DEFINITIONS: Record<
  NodeType,
  { label: string; color: string; icon: string }
> = {
  data_source: {
    label: "数据源",
    color: "border-blue-400 bg-blue-50",
    icon: "📊",
  },
  feature_engineering: {
    label: "特征工程",
    color: "border-yellow-400 bg-yellow-50",
    icon: "🔧",
  },
  model_training: {
    label: "模型训练",
    color: "border-green-400 bg-green-50",
    icon: "🧠",
  },
  evaluation: {
    label: "模型评估",
    color: "border-purple-400 bg-purple-50",
    icon: "📈",
  },
};
