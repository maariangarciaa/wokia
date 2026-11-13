export type DatasetItem = {
  file_name?: string;
  name?: string;
  rows?: number;
  columns?: number;
  [key: string]: unknown;
};

export type ColumnProfile = {
  name: string;
  dtype: string;
  kind: string;
  missing: number;
  missing_pct: number;
  unique: number;
  stats?: {
    mean?: number | null;
    std?: number | null;
    min?: number | null;
    median?: number | null;
    max?: number | null;
  };
  top_values?: Record<string, number>;
};

export type DatasetProfile = {
  file_name: string;
  shape: {
    rows: number;
    columns: number;
  };
  columns: ColumnProfile[];
  missing_total: number;
  duplicate_rows: number;
  numeric_columns: string[];
  categorical_columns: string[];
  preview: Record<string, unknown>[];
};

export type SummaryTask =
  | "structure"
  | "columns"
  | "missing"
  | "duplicates"
  | "correlations"
  | "feature_ideas"
  | "target"
  | "outliers";

export type AssistantSummaryResponse = {
  file_name: string;
  task: SummaryTask;
  mode: "llm" | "deterministic";
  answer: string;
};

export type UploadDatasetResponse = {
  file_name: string;
  metadata: Record<string, unknown>;
};

export type ChartRenderResponse = {
  file_name: string;
  question: string;
  source: "llm" | "fallback";
  fallback_used: boolean;
  mime_type: string;
  image_base64: string;
  code: string;
};

export type CausalCandidatesResponse = {
  file_name: string;
  question: string;
  objetivo: string | null;
  candidatas: string[];
  correlaciones: Record<string, number>;
  aviso?: string;
  error?: string;
  columnas_disponibles?: string[];
};

export type CausalHypothesesResponse = {
  file_name: string;
  objetivo: string;
  candidata: string;
  hipotesis: string[];
};

export type CausalTreatmentResponse = {
  file_name: string;
  hipotesis: string;
  explicacion: string;
  codigo: string;
  applied: boolean;
  treatment_counts: Record<string, number>;
  columns: string[];
  preview: Record<string, unknown>[];
};

export type CausalManualSetupResponse = {
  file_name: string;
  treatment: string;
  treatment_source: string;
  outcome: string;
  setup_code: string;
  treatment_counts: Record<string, number>;
  treatment_was_binary: boolean;
  treatment_value_1: string;
  treatment_value_0: string;
  outcome_was_converted: boolean;
  outcome_value_1: string | null;
  outcome_value_0: string | null;
  preview: Record<string, unknown>[];
};

export type CausalDagResponse = {
  file_name: string;
  outcome: string;
  treatment: string;
  source: "agent" | "deterministic_fallback" | string;
  dot: string;
  resumen: Record<string, unknown>;
  treatment_counts: Record<string, number>;
};

export type CausalIdentifyResponse = {
  file_name: string;
  outcome: string;
  treatment: string;
  criterio: string;
  backdoor_variables: string[];
  estimand_text: string;
  n_observations: number;
  graph_nodes: string[];
  graph_edges: Array<[string, string]>;
};

export type CausalMethodResponse = {
  file_name: string;
  treatment: string;
  backdoor_variables: string[];
  metodo_recomendado: string;
  justificacion: string;
  source: "agent" | "deterministic_fallback" | string;
  puntos_diagnostico: string[];
  aspectos_positivos: string[];
  cautelas: string[];
  diagnostico: Record<string, unknown>;
  raw_agent_response?: string | null;
};

export type CausalEstimateResponse = {
  file_name: string;
  outcome: string;
  treatment: string;
  metodo: string;
  estimate: number | null;
  intervalo_confianza: number[][] | null;
  intervalo_bajo: number | null;
  intervalo_alto: number | null;
  intervalo_incluye_cero: boolean | null;
  target_units: string | null;
  interpretacion: string;
  source: "agent" | "deterministic_fallback" | string;
  raw_agent_response?: string | null;
  error?: string | null;
};

export type CausalRefuteResponse = {
  file_name: string;
  outcome: string;
  treatment: string;
  metodo_estimacion: string;
  metodo_refutacion: string;
  estimate: number | null;
  new_effect: number | null;
  cambio_absoluto: number | null;
  cambio_relativo: number | null;
  p_valor: number | null;
  refutacion: string;
  interpretacion: string;
  source: "agent" | "deterministic_fallback" | string;
  raw_agent_response?: string | null;
  error?: string | null;
};

const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    throw new Error(`Error ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function getHealth() {
  return request<{ status: string; service: string }>("/health");
}

export async function getDatasets() {
  return request<{ datasets: DatasetItem[] }>("/datasets");
}

export async function uploadDataset(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadDatasetResponse>("/datasets/upload", {
    method: "POST",
    body: formData,
  });
}

export async function getDatasetProfile(fileName: string) {
  return request<DatasetProfile>(`/datasets/${encodeURIComponent(fileName)}/profile`);
}

export async function getAssistantSummary(fileName: string, task: SummaryTask) {
  return request<AssistantSummaryResponse>(`/datasets/${encodeURIComponent(fileName)}/assistant-summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ task }),
  });
}

export async function renderChart(fileName: string, question: string, preferFallback: boolean) {
  return request<ChartRenderResponse>(`/datasets/${encodeURIComponent(fileName)}/charts/render`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      prefer_fallback: preferFallback,
    }),
  });
}

export async function findCausalCandidates(fileName: string, question: string) {
  return request<CausalCandidatesResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
}

export async function generateCausalHypotheses(fileName: string, objetivo: string, candidata: string) {
  return request<CausalHypothesesResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/hypotheses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ objetivo, candidata }),
  });
}

export async function generateCausalTreatment(fileName: string, hipotesis: string) {
  return request<CausalTreatmentResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/treatment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ hipotesis, apply_code: true }),
  });
}

export async function createManualCausalSetup(fileName: string, treatmentSource: string, outcome: string) {
  return request<CausalManualSetupResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/manual-setup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      treatment_source: treatmentSource,
      outcome,
    }),
  });
}

export async function generateCausalDag(
  fileName: string,
  outcome: string,
  treatmentCode: string,
  useAgent = true,
) {
  return request<CausalDagResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/dag`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      outcome,
      treatment: "treatment",
      treatment_code: treatmentCode,
      use_agent: useAgent,
    }),
  });
}

export async function identifyCausalEffect(fileName: string, outcome: string, treatmentCode: string, dot: string) {
  return request<CausalIdentifyResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/identify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      outcome,
      treatment: "treatment",
      treatment_code: treatmentCode,
      dot,
    }),
  });
}

export async function recommendCausalMethod(
  fileName: string,
  treatmentCode: string,
  backdoorVariables: string[],
  useAgent = true,
) {
  return request<CausalMethodResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/method`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      treatment: "treatment",
      treatment_code: treatmentCode,
      backdoor_variables: backdoorVariables,
      use_agent: useAgent,
    }),
  });
}

export async function estimateCausalEffect(
  fileName: string,
  outcome: string,
  treatmentCode: string,
  dot: string,
  metodo: string,
  useAgent = true,
) {
  return request<CausalEstimateResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/estimate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      outcome,
      treatment: "treatment",
      treatment_code: treatmentCode,
      dot,
      metodo,
      use_agent: useAgent,
    }),
  });
}

export async function refuteCausalEffect(
  fileName: string,
  outcome: string,
  treatmentCode: string,
  dot: string,
  metodo: string,
  useAgent = true,
) {
  return request<CausalRefuteResponse>(`/datasets/${encodeURIComponent(fileName)}/causal/refute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      outcome,
      treatment: "treatment",
      treatment_code: treatmentCode,
      dot,
      metodo,
      use_agent: useAgent,
    }),
  });
}

export function getDatasetName(item: DatasetItem): string {
  return String(item.file_name ?? item.name ?? "");
}
