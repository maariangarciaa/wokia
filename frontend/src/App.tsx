import { useEffect, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity,
  BarChart3,
  Boxes,
  Brain,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  GitBranch,
  Lightbulb,
  Loader2,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sigma,
  Sparkles,
  Target,
  TriangleAlert,
} from "lucide-react";
import {
  AssistantSummaryResponse,
  ChartRenderResponse,
  CausalCandidatesResponse,
  CausalDagResponse,
  CausalEstimateResponse,
  CausalHypothesesResponse,
  CausalIdentifyResponse,
  CausalManualSetupResponse,
  CausalMethodResponse,
  CausalRefuteResponse,
  CausalTreatmentResponse,
  DatasetItem,
  DatasetProfile,
  SummaryTask,
  createManualCausalSetup,
  estimateCausalEffect,
  findCausalCandidates,
  generateCausalDag,
  generateCausalHypotheses,
  generateCausalTreatment,
  getAssistantSummary,
  getDatasetName,
  getDatasetProfile,
  getDatasets,
  getHealth,
  identifyCausalEffect,
  recommendCausalMethod,
  refuteCausalEffect,
  renderChart,
  uploadDataset,
} from "./api";

type ApiState = "checking" | "online" | "offline";
type ViewKey = "workspace" | "profile" | "charts" | "causal";

const navItems: Array<{
  key: ViewKey;
  label: string;
  helper: string;
  icon: typeof Boxes;
}> = [
  { key: "workspace", label: "Workspace", helper: "Estado y dataset", icon: Boxes },
  { key: "profile", label: "Perfilado", helper: "Estructura y calidad", icon: Database },
  { key: "charts", label: "Graficos", helper: "Visualizaciones", icon: BarChart3 },
  { key: "causal", label: "Causalidad", helper: "DAG y estimacion", icon: GitBranch },
];

const summaryTasks: Array<{
  key: SummaryTask;
  title: string;
  description: string;
  icon: typeof Brain;
}> = [
  {
    key: "structure",
    title: "Perfilado general",
    description: "Filas, columnas y tipo de variable de cada campo.",
    icon: Database,
  },
  {
    key: "columns",
    title: "Significado de columnas",
    description: "Lectura accesible del posible proposito de cada columna.",
    icon: MessageSquareText,
  },
  {
    key: "missing",
    title: "Valores nulos",
    description: "Calidad de datos y columnas con valores faltantes.",
    icon: TriangleAlert,
  },
  {
    key: "duplicates",
    title: "Duplicados",
    description: "Registros repetidos exactos y posible impacto.",
    icon: CheckCircle2,
  },
  {
    key: "correlations",
    title: "Correlaciones numericas",
    description: "Relaciones fuertes, debiles y posibles redundancias.",
    icon: Sigma,
  },
  {
    key: "feature_ideas",
    title: "Nuevas variables",
    description: "Ideas de variables derivadas con formula y utilidad.",
    icon: Lightbulb,
  },
  {
    key: "target",
    title: "Variable objetivo",
    description: "Candidata para modelado supervisado y justificacion.",
    icon: Target,
  },
  {
    key: "outliers",
    title: "Outliers",
    description: "Senales de valores extremos que conviene revisar.",
    icon: Search,
  },
];

const causalEstimationMethods = [
  "backdoor.linear_regression",
  "backdoor.propensity_score_matching",
  "backdoor.propensity_score_weighting",
  "backdoor.distance_matching",
  "backdoor.propensity_score_stratification",
  "iv.instrumental_variable",
  "iv.regression_discontinuity",
];

function BrandMark() {
  return (
    <div className="brand-mark" aria-label="Wokia">
      <svg aria-hidden="true" viewBox="0 0 72 72">
        <path className="brand-mark-echo" d="M9 20h10l10 31 9-25 12 31 13-39" />
        <path className="brand-mark-trace" d="M9 20h10l10 31 9-25 12 31 13-39" />
      </svg>
    </div>
  );
}

export function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [activeView, setActiveView] = useState<ViewKey>("workspace");
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [error, setError] = useState("");

  async function refreshDatasets(preferredDataset?: string) {
    const datasetResponse = await getDatasets();
    setDatasets(datasetResponse.datasets);
    const datasetNames = datasetResponse.datasets.map(getDatasetName).filter(Boolean);
    const nextDataset = preferredDataset && datasetNames.includes(preferredDataset) ? preferredDataset : datasetNames[0];
    if (nextDataset) {
      setSelectedDataset(nextDataset);
    }
  }

  useEffect(() => {
    async function bootstrap() {
      try {
        await getHealth();
        setApiState("online");
        await refreshDatasets();
      } catch (caughtError) {
        setApiState("offline");
        setError(caughtError instanceof Error ? caughtError.message : "No se pudo conectar con la API.");
      }
    }

    bootstrap();
  }, []);

  useEffect(() => {
    if (!selectedDataset) {
      setProfile(null);
      return;
    }

    async function loadProfile() {
      setLoadingProfile(true);
      setError("");
      try {
        const nextProfile = await getDatasetProfile(selectedDataset);
        setProfile(nextProfile);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "No se pudo cargar el perfil del dataset.");
        setProfile(null);
      } finally {
        setLoadingProfile(false);
      }
    }

    loadProfile();
  }, [selectedDataset]);

  const issueCount = (profile?.missing_total ?? 0) + (profile?.duplicate_rows ?? 0);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <BrandMark />
          <div>
            <p className="wordmark" aria-label="Wokia">
              <span>Wok</span>
              <span>ia</span>
            </p>
            <h1>Explora datos con criterio.</h1>
          </div>
        </div>

        <nav className="nav-list" aria-label="Navegacion principal">
          {navItems.map((item) => (
            <button
              className={`nav-item ${activeView === item.key ? "active" : ""}`}
              key={item.key}
              type="button"
              onClick={() => {
                setActiveView(item.key);
                window.scrollTo({ top: 0, behavior: "instant" });
              }}
            >
              <item.icon size={19} />
              <span>
                <strong>{item.label}</strong>
                <small>{item.helper}</small>
              </span>
            </button>
          ))}
        </nav>

      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="section-kicker">Workspace inteligente de datos</p>
            <h2 className="main-wordmark">
              <span>Wok</span>
              <span>ia</span>
            </h2>
          </div>
          <div className={`api-pill ${apiState}`}>
            {apiState === "checking" ? <Loader2 size={16} className="spin" /> : <Activity size={16} />}
            <span>
              {apiState === "online" ? "API conectada" : apiState === "offline" ? "API sin conexion" : "Comprobando API"}
            </span>
          </div>
        </header>

        {error && <div className="alert">{error}</div>}

        {activeView === "workspace" && (
          <WorkspaceView
            datasets={datasets}
            selectedDataset={selectedDataset}
            setSelectedDataset={setSelectedDataset}
            refreshDatasets={refreshDatasets}
            profile={profile}
            loadingProfile={loadingProfile}
            issueCount={issueCount}
          />
        )}

        {activeView === "profile" && (
          <ProfileView selectedDataset={selectedDataset} profile={profile} loadingProfile={loadingProfile} />
        )}

        {activeView === "charts" && (
          <ChartsView selectedDataset={selectedDataset} profile={profile} />
        )}

        {activeView === "causal" && (
          <CausalView selectedDataset={selectedDataset} profile={profile} />
        )}
      </main>
    </div>
  );
}

function WorkspaceView({
  datasets,
  selectedDataset,
  setSelectedDataset,
  refreshDatasets,
  profile,
  loadingProfile,
  issueCount,
}: {
  datasets: DatasetItem[];
  selectedDataset: string;
  setSelectedDataset: (dataset: string) => void;
  refreshDatasets: (preferredDataset?: string) => Promise<void>;
  profile: DatasetProfile | null;
  loadingProfile: boolean;
  issueCount: number;
}) {
  const [uploadingDataset, setUploadingDataset] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  async function handleDatasetUpload(file: File | undefined) {
    if (!file) {
      return;
    }
    setUploadingDataset(true);
    setUploadMessage("");
    setUploadError("");
    try {
      const result = await uploadDataset(file);
      await refreshDatasets(result.file_name);
      setUploadMessage(`${result.file_name} cargado correctamente.`);
    } catch (caughtError) {
      setUploadError(caughtError instanceof Error ? caughtError.message : "No se pudo subir el dataset.");
    } finally {
      setUploadingDataset(false);
    }
  }

  return (
    <>
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="product-chip">
            <Sparkles size={16} />
            Data workbench
          </span>
          <h3>Sube datos. Descubre senales. Decide con criterio.</h3>
          <p>
            Elige un dataset, revisa su salud inicial y prepara el terreno para resumen, graficos e inferencia causal
            con la API de Wokia.
          </p>
        </div>
        <div className="dataset-picker">
          <label htmlFor="dataset-select">Dataset activo</label>
          <div className="select-wrap">
            <FileSpreadsheet size={18} />
            <select
              id="dataset-select"
              value={selectedDataset}
              onChange={(event) => setSelectedDataset(event.target.value)}
              disabled={!datasets.length}
            >
              {!datasets.length && <option>No hay datasets disponibles</option>}
              {datasets.map((dataset) => {
                const name = getDatasetName(dataset);
                return (
                  <option key={name} value={name}>
                    {name}
                  </option>
                );
              })}
            </select>
          </div>
          <label className="upload-dropzone">
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => handleDatasetUpload(event.target.files?.[0])}
              disabled={uploadingDataset}
            />
            <FileSpreadsheet size={18} />
            <span>{uploadingDataset ? "Subiendo dataset..." : "Subir CSV o Excel"}</span>
          </label>
          {uploadMessage && <p className="upload-status ok">{uploadMessage}</p>}
          {uploadError && <p className="upload-status error">{uploadError}</p>}
          <div className="tech-visual" aria-hidden="true">
            <div className="visual-grid">
              {Array.from({ length: 18 }).map((_, index) => (
                <span key={index} />
              ))}
            </div>
            <div className="visual-line one" />
            <div className="visual-line two" />
            <div className="visual-stat">
              <strong>{profile?.shape.rows ?? "--"}</strong>
              <span>filas listas</span>
            </div>
          </div>
        </div>
      </section>

      <section className="welcome-panel">
        <div className="welcome-copy">
          <p className="panel-kicker">Bienvenida a Wokia</p>
          <h3>Un mini data scientist para abrir un dataset nuevo sin partir de cero.</h3>
          <p>
            Wokia nace como un TFG y evoluciona hacia un workspace inteligente: te ayuda a entender estructura,
            detectar primeras senales, pedir graficos en lenguaje natural y explorar hipotesis causales con criterio.
          </p>
        </div>
        <div className="welcome-orbit" aria-hidden="true">
          <span />
          <span />
          <span />
          <BrandMark />
        </div>
      </section>

      <section className="usage-flow" aria-label="Como usar Wokia">
        {[
          {
            title: "Sube",
            text: "Carga un CSV o Excel y deja que Wokia prepare el contexto.",
            icon: FileSpreadsheet,
          },
          {
            title: "Entiende",
            text: "Revisa estructura, calidad, nulos, duplicados y primeras lecturas.",
            icon: Database,
          },
          {
            title: "Visualiza",
            text: "Pide graficos con una frase y descarga resultados listos para documentar.",
            icon: BarChart3,
          },
          {
            title: "Razona",
            text: "Plantea hipotesis, genera DAGs y estima efectos causales cuando tenga sentido.",
            icon: GitBranch,
          },
        ].map((step, index, steps) => (
          <div className="flow-step" key={step.title}>
            <div className="flow-index">0{index + 1}</div>
            <step.icon size={22} />
            <h4>{step.title}</h4>
            <p>{step.text}</p>
            {index < steps.length - 1 && <div className="flow-arrow" aria-hidden="true" />}
          </div>
        ))}
      </section>

      <section className="module-map" aria-label="Modulos de Wokia">
        <article>
          <span className="module-glow profile" />
          <Database size={22} />
          <h4>Perfilado asistido</h4>
          <p>Ocho tareas guiadas para entender el dataset, su calidad y posibles variables utiles.</p>
        </article>
        <article>
          <span className="module-glow charts" />
          <BarChart3 size={22} />
          <h4>Graficos por lenguaje natural</h4>
          <p>Escribe lo que quieres ver y Wokia genera codigo Python, ejecuta la visualizacion y devuelve PNG.</p>
        </article>
        <article>
          <span className="module-glow causal" />
          <GitBranch size={22} />
          <h4>Causalidad exploratoria</h4>
          <p>De pregunta causal a treatment, DAG editable, identificabilidad, metodo, estimacion y robustez.</p>
        </article>
      </section>

      <section className="metric-grid" aria-label="Resumen del dataset">
        <MetricCard label="Filas" value={profile?.shape.rows ?? "-"} helper="observaciones" />
        <MetricCard label="Columnas" value={profile?.shape.columns ?? "-"} helper="variables" />
        <MetricCard
          label="Nulos"
          value={profile?.missing_total ?? "-"}
          helper="valores faltantes"
          tone={profile?.missing_total ? "warn" : "ok"}
        />
        <MetricCard
          label="Duplicados"
          value={profile?.duplicate_rows ?? "-"}
          helper="filas exactas"
          tone={profile?.duplicate_rows ? "warn" : "ok"}
        />
      </section>

      <section className="content-grid">
        <article className="panel">
          <div className="panel-heading compact">
            <div>
              <p className="panel-kicker">Primer vistazo</p>
              <h3>{profile?.file_name ?? "Sin dataset"}</h3>
            </div>
            {loadingProfile && <Loader2 size={18} className="spin muted" />}
          </div>
          <p className="quality-copy">
            {profile
              ? `Dataset listo para explorar: ${profile.shape.rows} filas, ${profile.shape.columns} columnas y ${profile.numeric_columns.length} variables numericas detectadas.`
              : "Selecciona un dataset para cargar su perfil inicial."}
          </p>
          <div className="mini-list two-columns">
            <span>{profile?.numeric_columns.length ?? 0} numericas</span>
            <span>{profile?.categorical_columns.length ?? 0} categoricas</span>
            <span>{profile?.missing_total ?? 0} nulos</span>
            <span>{profile?.duplicate_rows ?? 0} duplicados</span>
          </div>
        </article>

        <aside className="panel">
          <div className="panel-heading compact">
            <div>
              <p className="panel-kicker">Calidad</p>
              <h3>Lectura rapida</h3>
            </div>
            <Search size={18} />
          </div>
          <div className={`quality-score ${issueCount ? "warn" : "ok"}`}>{issueCount ? "Revisar" : "Limpio"}</div>
          <p className="quality-copy">
            {issueCount
              ? "Hay senales que conviene revisar antes de modelar o interpretar resultados."
              : "No se detectan nulos ni duplicados exactos en este perfil inicial."}
          </p>
        </aside>
      </section>
    </>
  );
}

function CausalView({
  selectedDataset,
  profile,
}: {
  selectedDataset: string;
  profile: DatasetProfile | null;
}) {
  const columns = profile?.columns.map((column) => column.name) ?? [];
  const numericColumns = profile?.numeric_columns ?? [];
  const [mode, setMode] = useState<"question" | "manual">("question");
  const [causalQuestion, setCausalQuestion] = useState("que variables influyen en PriceEuro");
  const [candidateResult, setCandidateResult] = useState<CausalCandidatesResponse | null>(null);
  const [candidateChoiceMode, setCandidateChoiceMode] = useState<"suggested" | "manual">("suggested");
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [manualCandidate, setManualCandidate] = useState("");
  const [hypothesesResult, setHypothesesResult] = useState<CausalHypothesesResponse | null>(null);
  const [selectedHypothesis, setSelectedHypothesis] = useState("");
  const [customHypothesis, setCustomHypothesis] = useState("");
  const [treatmentResult, setTreatmentResult] = useState<CausalTreatmentResponse | null>(null);
  const [manualTreatmentCol, setManualTreatmentCol] = useState("");
  const [manualOutcome, setManualOutcome] = useState("");
  const [manualSetup, setManualSetup] = useState<CausalManualSetupResponse | null>(null);
  const [loadingCausal, setLoadingCausal] = useState("");
  const [causalError, setCausalError] = useState("");

  useEffect(() => {
    setCandidateResult(null);
    setHypothesesResult(null);
    setTreatmentResult(null);
    setManualSetup(null);
    setSelectedCandidate("");
    setManualCandidate("");
    setSelectedHypothesis("");
    setCustomHypothesis("");
    setCausalError("");
  }, [selectedDataset, mode]);

  useEffect(() => {
    if (!manualTreatmentCol && columns.length) {
      setManualTreatmentCol(columns[0]);
    }
    if (!manualOutcome && numericColumns.length) {
      setManualOutcome(numericColumns[0]);
    }
  }, [columns, manualOutcome, manualTreatmentCol, numericColumns]);

  const objective = candidateResult?.objetivo ?? "";
  const candidateOptions =
    candidateChoiceMode === "suggested"
      ? candidateResult?.candidatas ?? []
      : columns.filter((column) => column !== objective);
  const effectiveCandidate = candidateChoiceMode === "suggested" ? selectedCandidate : manualCandidate;
  const effectiveHypothesis = selectedHypothesis === "__custom__" ? customHypothesis : selectedHypothesis;
  const treatmentColumnMeta = profile?.columns.find((column) => column.name === manualTreatmentCol);
  const outcomeColumnMeta = profile?.columns.find((column) => column.name === manualOutcome);
  const treatmentIsBinary = treatmentColumnMeta?.unique === 2;
  const outcomeIsNumeric = outcomeColumnMeta?.kind === "numeric";
  const outcomeIsBinary = outcomeColumnMeta?.unique === 2;
  const outcomeIsValid = Boolean(outcomeColumnMeta && (outcomeIsNumeric || outcomeIsBinary));
  const activeTreatmentCode = treatmentResult?.codigo ?? manualSetup?.setup_code ?? "";
  const activeOutcome = treatmentResult ? objective : manualSetup?.outcome ?? "";

  async function runCandidates() {
    if (!selectedDataset || !causalQuestion.trim()) {
      return;
    }
    setLoadingCausal("candidates");
    setCausalError("");
    setCandidateResult(null);
    setHypothesesResult(null);
    setTreatmentResult(null);
    try {
      const result = await findCausalCandidates(selectedDataset, causalQuestion.trim());
      setCandidateResult(result);
      setSelectedCandidate(result.candidatas[0] ?? "");
    } catch (caughtError) {
      setCausalError(caughtError instanceof Error ? caughtError.message : "No se pudieron encontrar candidatas.");
    } finally {
      setLoadingCausal("");
    }
  }

  async function runHypotheses() {
    if (!selectedDataset || !objective || !effectiveCandidate) {
      return;
    }
    setLoadingCausal("hypotheses");
    setCausalError("");
    setHypothesesResult(null);
    setTreatmentResult(null);
    try {
      const result = await generateCausalHypotheses(selectedDataset, objective, effectiveCandidate);
      setHypothesesResult(result);
      setSelectedHypothesis(result.hipotesis[0] ?? "");
    } catch (caughtError) {
      setCausalError(caughtError instanceof Error ? caughtError.message : "No se pudieron generar hipotesis.");
    } finally {
      setLoadingCausal("");
    }
  }

  async function runTreatmentFromHypothesis() {
    if (!selectedDataset || !effectiveHypothesis.trim()) {
      return;
    }
    setLoadingCausal("treatment");
    setCausalError("");
    setTreatmentResult(null);
    try {
      const result = await generateCausalTreatment(selectedDataset, effectiveHypothesis.trim());
      setTreatmentResult(result);
    } catch (caughtError) {
      setCausalError(caughtError instanceof Error ? caughtError.message : "No se pudo crear treatment.");
    } finally {
      setLoadingCausal("");
    }
  }

  async function runManualSetup() {
    if (!selectedDataset || !manualTreatmentCol || !manualOutcome) {
      return;
    }
    if (!outcomeIsValid) {
      setCausalError("La variable resultado debe ser numerica o binaria. Selecciona otra columna.");
      return;
    }
    setLoadingCausal("manual");
    setCausalError("");
    setManualSetup(null);
    try {
      const result = await createManualCausalSetup(selectedDataset, manualTreatmentCol, manualOutcome);
      setManualSetup(result);
    } catch (caughtError) {
      setCausalError(caughtError instanceof Error ? caughtError.message : "No se pudo preparar el tratamiento manual.");
    } finally {
      setLoadingCausal("");
    }
  }

  return (
    <>
      <section className="page-intro causal-hero">
        <div>
          <p className="section-kicker">Causalidad</p>
          <h3>Plantea una hipotesis. Explora su efecto.</h3>
          <p>
            Define el punto de partida y avanza paso a paso: treatment, DAG editable, identificabilidad, estimacion y
            robustez.
          </p>
          <div className="causal-hero-tags">
            <span>Dos recorridos posibles</span>
            <span>DAG editable</span>
            <span>Estimacion guiada</span>
          </div>
        </div>
        <span className="dataset-name">{profile?.file_name ?? selectedDataset}</span>
      </section>

      <section className="causal-route-intro">
        <p className="section-kicker">Elige el punto de partida</p>
        <h3>Dos caminos para comenzar el analisis causal.</h3>
        <p>
          Deja que Wokia proponga variables a partir de una pregunta o configura directamente el tratamiento que
          quieres estudiar.
        </p>
      </section>

      <section className="causal-mode-switch">
        <button
          className={`mode-card question ${mode === "question" ? "active" : ""}`}
          type="button"
          onClick={() => setMode("question")}
        >
          <div className="mode-card-icon">
            <Brain size={22} />
          </div>
          <span>
            <small className="mode-card-route">Ruta 01 / Con asistente</small>
            <strong>Formular pregunta causal</strong>
            <small>Wokia detecta objetivo, variables candidatas y propone hipotesis.</small>
            <b>Empezar por aqui</b>
          </span>
        </button>
        <button
          className={`mode-card manual ${mode === "manual" ? "active" : ""}`}
          type="button"
          onClick={() => setMode("manual")}
        >
          <div className="mode-card-icon">
            <GitBranch size={22} />
          </div>
          <span>
            <small className="mode-card-route">Ruta 02 / Configuracion manual</small>
            <strong>Seleccionar tratamiento manual</strong>
            <small>Elige tratamiento y resultado; se genera `treatment` binario automaticamente.</small>
            <b>Configurar tratamiento</b>
          </span>
        </button>
      </section>

      {causalError && <div className="alert">{causalError}</div>}

      {mode === "question" ? (
        <section className="causal-flow-grid">
          <article className="panel causal-step">
            <div className="step-badge">1</div>
            <div>
              <p className="panel-kicker">Pregunta causal</p>
              <h3>Busca variables candidatas</h3>
            </div>
            <textarea
              className="prompt-input"
              value={causalQuestion}
              onChange={(event) => setCausalQuestion(event.target.value)}
              rows={3}
              placeholder="Ej: que variables influyen en PriceEuro"
            />
            <button
              className="task-button primary"
              type="button"
              onClick={runCandidates}
              disabled={!selectedDataset || !causalQuestion.trim() || Boolean(loadingCausal)}
            >
              {loadingCausal === "candidates" ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Analizando
                </>
              ) : (
                "Encontrar candidatas"
              )}
            </button>

            {candidateResult && (
              <div className="causal-result-box">
                <strong>Objetivo detectado: {candidateResult.objetivo ?? "No identificado"}</strong>
                <div className="correlation-list">
                  {Object.entries(candidateResult.correlaciones).map(([column, value]) => (
                    <span key={column}>
                      {column}: {value}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </article>

          <article className="panel causal-step">
            <div className="step-badge">2</div>
            <div>
              <p className="panel-kicker">Variable candidata</p>
              <h3>Elige causa posible</h3>
            </div>

            <div className="segmented-control">
              <button
                className={candidateChoiceMode === "suggested" ? "active" : ""}
                type="button"
                onClick={() => setCandidateChoiceMode("suggested")}
                disabled={!candidateResult}
              >
                Sugeridas
              </button>
              <button
                className={candidateChoiceMode === "manual" ? "active" : ""}
                type="button"
                onClick={() => setCandidateChoiceMode("manual")}
                disabled={!candidateResult}
              >
                Manual
              </button>
            </div>

            <select
              className="select-field"
              value={effectiveCandidate}
              onChange={(event) =>
                candidateChoiceMode === "suggested"
                  ? setSelectedCandidate(event.target.value)
                  : setManualCandidate(event.target.value)
              }
              disabled={!candidateResult || !candidateOptions.length}
            >
              {!candidateOptions.length && <option>No hay candidatas disponibles</option>}
              {candidateOptions.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>

            <button
              className="task-button primary"
              type="button"
              onClick={runHypotheses}
              disabled={!selectedDataset || !objective || !effectiveCandidate || Boolean(loadingCausal)}
            >
              {loadingCausal === "hypotheses" ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Generando
                </>
              ) : (
                "Generar hipotesis"
              )}
            </button>
          </article>

          <article className="panel causal-step wide-step">
            <div className="step-badge">3</div>
            <div>
              <p className="panel-kicker">Hipotesis</p>
              <h3>Selecciona o escribe la hipotesis causal</h3>
            </div>

            <div className="hypothesis-list">
              {(hypothesesResult?.hipotesis ?? []).map((hypothesis) => (
                <label className="hypothesis-option" key={hypothesis}>
                  <input
                    type="radio"
                    name="hypothesis"
                    value={hypothesis}
                    checked={selectedHypothesis === hypothesis}
                    onChange={() => setSelectedHypothesis(hypothesis)}
                  />
                  <span>{hypothesis}</span>
                </label>
              ))}
              <label className="hypothesis-option">
                <input
                  type="radio"
                  name="hypothesis"
                  value="__custom__"
                  checked={selectedHypothesis === "__custom__"}
                  onChange={() => setSelectedHypothesis("__custom__")}
                />
                <span>Quiero escribir mi propia hipotesis</span>
              </label>
            </div>

            {selectedHypothesis === "__custom__" && (
              <textarea
                className="prompt-input"
                value={customHypothesis}
                onChange={(event) => setCustomHypothesis(event.target.value)}
                rows={3}
                placeholder="Ej: Los vehiculos con mayor velocidad maxima tienden a tener precios mas altos."
              />
            )}

            <button
              className="task-button primary"
              type="button"
              onClick={runTreatmentFromHypothesis}
              disabled={!selectedDataset || !effectiveHypothesis.trim() || Boolean(loadingCausal)}
            >
              {loadingCausal === "treatment" ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Creando treatment
                </>
              ) : (
                "Generar columna treatment"
              )}
            </button>

            {treatmentResult && (
              <CausalSetupSummary
                code={treatmentResult.codigo}
                counts={treatmentResult.treatment_counts}
                explanation={treatmentResult.explicacion}
                preview={treatmentResult.preview}
              />
            )}
          </article>
        </section>
      ) : (
        <section className="manual-causal-panel panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Seleccion manual</p>
              <h3>Tratamiento y resultado</h3>
            </div>
          </div>

          <div className="manual-grid">
            <label>
              <span>Columna de tratamiento</span>
              <select
                className="select-field"
                value={manualTreatmentCol}
                onChange={(event) => setManualTreatmentCol(event.target.value)}
              >
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
              {treatmentColumnMeta && (
                <div className={`type-note ${treatmentIsBinary ? "ok" : "warn"}`}>
                  {treatmentIsBinary
                    ? "Tratamiento binario detectado. El backend lo codificara como treatment 0/1."
                    : "Esta columna no es binaria. Wokia creara automaticamente treatment 0/1 y mostrara la regla exacta al confirmar."}
                </div>
              )}
            </label>

            <label>
              <span>Variable resultado</span>
              <select
                className="select-field"
                value={manualOutcome}
                onChange={(event) => setManualOutcome(event.target.value)}
              >
                {columns
                  .filter((column) => column !== manualTreatmentCol)
                  .map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
              </select>
              {outcomeColumnMeta && (
                <div className={`type-note ${outcomeIsNumeric ? "ok" : outcomeIsBinary ? "warn" : "error"}`}>
                  {outcomeIsNumeric &&
                    "Outcome numerico valido. No necesita transformacion antes de estimar el efecto."}
                  {!outcomeIsNumeric &&
                    outcomeIsBinary &&
                    "Outcome binario convertible. Si no esta en 0/1, el backend lo transformara y mostrara la equivalencia."}
                  {!outcomeIsNumeric &&
                    !outcomeIsBinary &&
                    "Outcome no valido para este flujo: debe ser numerico o binario. Elige otra variable resultado."}
                </div>
              )}
            </label>
          </div>

          <button
            className="task-button primary"
            type="button"
            onClick={runManualSetup}
            disabled={
              !selectedDataset ||
              !manualTreatmentCol ||
              !manualOutcome ||
              !outcomeIsValid ||
              Boolean(loadingCausal)
            }
          >
            {loadingCausal === "manual" ? (
              <>
                <Loader2 size={16} className="spin" />
                Preparando
              </>
            ) : (
              "Confirmar tratamiento y resultado"
            )}
          </button>

          {manualSetup && (
            <CausalSetupSummary
              code={manualSetup.setup_code}
              counts={manualSetup.treatment_counts}
              explanation={`Se ha creado treatment desde ${manualSetup.treatment_source}. Valor 1: ${manualSetup.treatment_value_1}; valor 0: ${manualSetup.treatment_value_0}.`}
              preview={manualSetup.preview}
              extra={
                manualSetup.outcome_was_converted
                  ? `La variable resultado ${manualSetup.outcome} tambien se convirtio a binaria. Valor 1: ${manualSetup.outcome_value_1}; valor 0: ${manualSetup.outcome_value_0}.`
                  : `La variable resultado ${manualSetup.outcome} es valida sin transformacion adicional.`
              }
            />
          )}
        </section>
      )}

      {activeTreatmentCode && activeOutcome && selectedDataset && (
        <CausalPipeline
          selectedDataset={selectedDataset}
          outcome={activeOutcome}
          treatmentCode={activeTreatmentCode}
        />
      )}
    </>
  );
}

function CausalSetupSummary({
  code,
  counts,
  explanation,
  preview,
  extra,
}: {
  code: string;
  counts: Record<string, number>;
  explanation: string;
  preview?: Record<string, unknown>[];
  extra?: string;
}) {
  const previewColumns = preview?.length ? Object.keys(preview[0]) : [];

  return (
    <div className="causal-setup-summary">
      <div className="causal-counts">
        {Object.entries(counts).map(([group, count]) => (
          <span key={group}>
            Grupo {group}: <strong>{count}</strong>
          </span>
        ))}
      </div>
      <TreatmentExplanation text={explanation} />
      {extra && <TreatmentExplanation text={extra} compact />}
      {preview?.length ? (
        <div className="treatment-preview">
          <strong>Vista previa del dataset con treatment</strong>
          <div className="preview-table-wrap">
            <table>
              <thead>
                <tr>
                  {previewColumns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((row, index) => (
                  <tr key={index}>
                    {previewColumns.map((column) => (
                      <td key={column}>{String(row[column] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      <details className="code-disclosure light">
        <summary>Ver codigo aplicado</summary>
        <pre>
          <code>{code}</code>
        </pre>
      </details>
    </div>
  );
}

function TreatmentExplanation({ text, compact = false }: { text: string; compact?: boolean }) {
  const sentences = text
    .replace(/\r/g, "")
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);

  return (
    <div className={`treatment-explanation ${compact ? "compact" : ""}`}>
      <strong>{compact ? "Resultado" : "Como se ha creado treatment"}</strong>
      <div>
        {sentences.map((sentence, index) => (
          <p key={`${index}-${sentence.slice(0, 24)}`}>{renderInlineMarkdown(sentence)}</p>
        ))}
      </div>
    </div>
  );
}

function CausalPipeline({
  selectedDataset,
  outcome,
  treatmentCode,
}: {
  selectedDataset: string;
  outcome: string;
  treatmentCode: string;
}) {
  const [dagResult, setDagResult] = useState<CausalDagResponse | null>(null);
  const [identifyResult, setIdentifyResult] = useState<CausalIdentifyResponse | null>(null);
  const [methodResult, setMethodResult] = useState<CausalMethodResponse | null>(null);
  const [selectedMethod, setSelectedMethod] = useState("");
  const [estimateResult, setEstimateResult] = useState<CausalEstimateResponse | null>(null);
  const [refuteResult, setRefuteResult] = useState<CausalRefuteResponse | null>(null);
  const [acceptedDot, setAcceptedDot] = useState("");
  const [draftDot, setDraftDot] = useState("");
  const [loadingStep, setLoadingStep] = useState("");
  const [pipelineError, setPipelineError] = useState("");

  useEffect(() => {
    setDagResult(null);
    setIdentifyResult(null);
    setMethodResult(null);
    setSelectedMethod("");
    setEstimateResult(null);
    setRefuteResult(null);
    setAcceptedDot("");
    setDraftDot("");
    setPipelineError("");
  }, [selectedDataset, outcome, treatmentCode]);

  async function runDag() {
    setLoadingStep("dag");
    setPipelineError("");
    setDagResult(null);
    setIdentifyResult(null);
    setMethodResult(null);
    setSelectedMethod("");
    setEstimateResult(null);
    setRefuteResult(null);
    try {
      const result = await generateCausalDag(selectedDataset, outcome, treatmentCode, true);
      setDagResult(result);
      setAcceptedDot(result.dot);
      setDraftDot(result.dot);
    } catch (caughtError) {
      setPipelineError(caughtError instanceof Error ? caughtError.message : "No se pudo generar el DAG.");
    } finally {
      setLoadingStep("");
    }
  }

  async function runIdentify() {
    if (!dagResult) {
      return;
    }
    setLoadingStep("identify");
    setPipelineError("");
    setIdentifyResult(null);
    setMethodResult(null);
    setSelectedMethod("");
    setEstimateResult(null);
    setRefuteResult(null);
    try {
      const result = await identifyCausalEffect(selectedDataset, outcome, treatmentCode, acceptedDot || dagResult.dot);
      setIdentifyResult(result);
    } catch (caughtError) {
      setPipelineError(caughtError instanceof Error ? caughtError.message : "No se pudo identificar el efecto.");
    } finally {
      setLoadingStep("");
    }
  }

  async function runMethod() {
    if (!identifyResult) {
      return;
    }
    setLoadingStep("method");
    setPipelineError("");
    setMethodResult(null);
    setSelectedMethod("");
    setEstimateResult(null);
    setRefuteResult(null);
    try {
      const result = await recommendCausalMethod(
        selectedDataset,
        treatmentCode,
        identifyResult.backdoor_variables,
        true,
      );
      setMethodResult(result);
      setSelectedMethod(result.metodo_recomendado);
    } catch (caughtError) {
      setPipelineError(caughtError instanceof Error ? caughtError.message : "No se pudo recomendar metodo.");
    } finally {
      setLoadingStep("");
    }
  }

  async function runEstimate() {
    if (!dagResult || !methodResult || !selectedMethod) {
      return;
    }
    setLoadingStep("estimate");
    setPipelineError("");
    setEstimateResult(null);
    setRefuteResult(null);
    try {
      const result = await estimateCausalEffect(
        selectedDataset,
        outcome,
        treatmentCode,
        acceptedDot || dagResult.dot,
        selectedMethod,
        true,
      );
      setEstimateResult(result);
    } catch (caughtError) {
      setPipelineError(caughtError instanceof Error ? caughtError.message : "No se pudo estimar el efecto.");
    } finally {
      setLoadingStep("");
    }
  }

  async function runRefute() {
    if (!dagResult || !methodResult || !selectedMethod) {
      return;
    }
    setLoadingStep("refute");
    setPipelineError("");
    setRefuteResult(null);
    try {
      const result = await refuteCausalEffect(
        selectedDataset,
        outcome,
        treatmentCode,
        acceptedDot || dagResult.dot,
        selectedMethod,
        true,
      );
      setRefuteResult(result);
    } catch (caughtError) {
      setPipelineError(caughtError instanceof Error ? caughtError.message : "No se pudo validar la robustez.");
    } finally {
      setLoadingStep("");
    }
  }

  function acceptDraftDot() {
    setAcceptedDot(draftDot);
    setIdentifyResult(null);
    setMethodResult(null);
    setSelectedMethod("");
    setEstimateResult(null);
    setRefuteResult(null);
  }

  function resetDraftDot() {
    setDraftDot(acceptedDot || dagResult?.dot || "");
  }

  const hasDraftChanges = Boolean(dagResult && draftDot && draftDot !== acceptedDot);

  return (
    <section className="panel causal-pipeline-panel">
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">Analisis causal</p>
          <h3>Continuar con DAG, estimacion y robustez</h3>
          <p className="panel-subtle">
            Resultado activo: <strong>{outcome}</strong>. Cada paso se ejecuta solo cuando lo pidas.
          </p>
        </div>
        <ShieldCheck size={22} className="muted" />
      </div>

      {pipelineError && <div className="task-error">{pipelineError}</div>}

      <div className="causal-pipeline-grid">
        <CausalActionCard
          number="1"
          title="DAG causal"
          description="Propone el grafo de supuestos a partir de treatment, outcome y variables del dataset."
          buttonLabel="Generar DAG"
          loading={loadingStep === "dag"}
          disabled={Boolean(loadingStep)}
          onClick={runDag}
        >
          {dagResult && (
            <div className="dag-result">
              <div className="dag-toolbar">
                <span>Fuente: {dagResult.source}</span>
                <span>{dagResult.treatment_counts["1"] ?? 0} tratados</span>
                {hasDraftChanges && <span>Borrador sin aceptar</span>}
              </div>
              <DagDiagram dot={acceptedDot || dagResult.dot} />
              <details className="code-disclosure light">
                <summary>Editar grafo y previsualizar cambios</summary>
                <div className="dag-editor-layout">
                  <label>
                    <span>DOT editable</span>
                    <textarea
                      className="dot-editor"
                      value={draftDot}
                      onChange={(event) => setDraftDot(event.target.value)}
                      rows={12}
                    />
                  </label>
                  <div>
                    <span className="editor-label">Previsualizacion del borrador</span>
                    <DagDiagram dot={draftDot} compact />
                  </div>
                </div>
                <div className="editor-actions">
                  <button className="task-button primary" type="button" onClick={acceptDraftDot} disabled={!hasDraftChanges}>
                    Aceptar cambios del grafo
                  </button>
                  <button className="task-button secondary" type="button" onClick={resetDraftDot} disabled={!hasDraftChanges}>
                    Descartar cambios
                  </button>
                </div>
                <p className="edit-hint">
                  Los pasos siguientes usan el grafo aceptado. Al aceptar cambios, vuelve a ejecutar identificabilidad.
                </p>
              </details>
            </div>
          )}
        </CausalActionCard>

        <CausalActionCard
          number="2"
          title="Identificabilidad"
          description="Comprueba si el efecto puede estimarse con criterio backdoor y variables de ajuste."
          buttonLabel="Identificar efecto"
          loading={loadingStep === "identify"}
          disabled={!dagResult || Boolean(loadingStep)}
          onClick={runIdentify}
        >
          {identifyResult && (
            <IdentificationResultPanel result={identifyResult} />
          )}
        </CausalActionCard>

        <CausalActionCard
          number="3"
          title="Metodo"
          description="El agente revisa el diagnostico y recomienda el metodo de estimacion mas prudente."
          buttonLabel="Recomendar metodo"
          loading={loadingStep === "method"}
          disabled={!identifyResult || Boolean(loadingStep)}
          onClick={runMethod}
        >
          {methodResult && (
            <MethodRecommendationPanel
              result={methodResult}
              selectedMethod={selectedMethod}
              setSelectedMethod={(method) => {
                setSelectedMethod(method);
                setEstimateResult(null);
                setRefuteResult(null);
                setPipelineError("");
              }}
            />
          )}
        </CausalActionCard>

        <CausalActionCard
          number="4"
          title="Estimacion"
          description="Calcula el efecto causal con DoWhy y pide al agente una lectura comprensible."
          buttonLabel="Estimar efecto"
          loading={loadingStep === "estimate"}
          disabled={!methodResult || !selectedMethod || !dagResult || Boolean(loadingStep)}
          onClick={runEstimate}
        >
          {estimateResult && (
            <div className="compact-result">
              <span>Efecto: {formatMaybeNumber(estimateResult.estimate)}</span>
              <span>
                IC: {formatMaybeNumber(estimateResult.intervalo_bajo)} -{" "}
                {formatMaybeNumber(estimateResult.intervalo_alto)}
              </span>
              <AgentInsightCards text={estimateResult.interpretacion} />
            </div>
          )}
        </CausalActionCard>

        <CausalActionCard
          number="5"
          title="Robustez"
          description="Ejecuta una refutacion random common cause para comprobar sensibilidad."
          buttonLabel="Validar robustez"
          loading={loadingStep === "refute"}
          disabled={!estimateResult || !methodResult || !selectedMethod || !dagResult || Boolean(loadingStep)}
          onClick={runRefute}
        >
          {refuteResult && (
            <div className="compact-result">
              <span>Nuevo efecto: {formatMaybeNumber(refuteResult.new_effect)}</span>
              <span>Cambio relativo: {formatMaybeNumber(refuteResult.cambio_relativo)}</span>
              <AgentInsightCards text={refuteResult.interpretacion} />
            </div>
          )}
        </CausalActionCard>
      </div>
    </section>
  );
}

function CausalActionCard({
  number,
  title,
  description,
  buttonLabel,
  loading,
  disabled,
  onClick,
  children,
}: {
  number: string;
  title: string;
  description: string;
  buttonLabel: string;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <article className="causal-action-card">
      <div className="step-badge">{number}</div>
      <div className="causal-action-body">
        <h4>{title}</h4>
        <p>{description}</p>
        <button className="task-button primary" type="button" onClick={onClick} disabled={disabled}>
          {loading ? (
            <>
              <Loader2 size={16} className="spin" />
              Ejecutando
            </>
          ) : (
            buttonLabel
          )}
        </button>
        {children}
      </div>
    </article>
  );
}

function IdentificationResultPanel({ result }: { result: CausalIdentifyResponse }) {
  const backdoorText = result.backdoor_variables.length
    ? result.backdoor_variables.join(", ")
    : "No se han detectado variables backdoor.";

  return (
    <div className="identification-panel">
      <div className="identification-summary">
        <div>
          <span>Criterio usado</span>
          <strong>{result.criterio}</strong>
        </div>
        <div>
          <span>Observaciones</span>
          <strong>{result.n_observations}</strong>
        </div>
        <div>
          <span>Nodos / flechas</span>
          <strong>
            {result.graph_nodes.length} / {result.graph_edges.length}
          </strong>
        </div>
      </div>

      <div className="friendly-explanation">
        <strong>Lectura del resultado</strong>
        <p>
          El efecto de <code>{result.treatment}</code> sobre <code>{result.outcome}</code> se puede estimar ajustando
          por las variables de confusión detectadas en el DAG.
        </p>
      </div>

      <div className="adjustment-box">
        <strong>Variables de ajuste recomendadas</strong>
        <div className="chip-row">
          {result.backdoor_variables.length ? (
            result.backdoor_variables.map((variable) => <span key={variable}>{variable}</span>)
          ) : (
            <span>Sin ajuste backdoor</span>
          )}
        </div>
        <p>Estas variables se usarán en el siguiente paso para escoger el metodo de estimacion.</p>
      </div>

      <details className="code-disclosure light">
        <summary>Ver estimando tecnico</summary>
        <pre>
          <code>{result.estimand_text || `Backdoor variables: ${backdoorText}`}</code>
        </pre>
      </details>
    </div>
  );
}

function MethodRecommendationPanel({
  result,
  selectedMethod,
  setSelectedMethod,
}: {
  result: CausalMethodResponse;
  selectedMethod: string;
  setSelectedMethod: (method: string) => void;
}) {
  const isRecommendedMethod = selectedMethod === result.metodo_recomendado;

  return (
    <div className="method-panel">
      <div className="method-hero">
        <div>
          <span>Metodo recomendado</span>
          <strong>{result.metodo_recomendado}</strong>
        </div>
        <span className={`source-pill ${result.source === "agent" ? "agent" : ""}`}>
          {result.source === "agent" ? "Agente" : "Fallback"}
        </span>
      </div>

      <div className="method-columns">
        <MethodList title="Diagnostico del dataset" items={result.puntos_diagnostico} tone="neutral" />
        <MethodList title="Lo que esta bien" items={result.aspectos_positivos} tone="positive" />
        <MethodList title="Cautelas" items={result.cautelas} tone="warning" />
      </div>

      <div className="agent-justification">
        <strong>Conclusion del agente</strong>
        <ReadableAgentMarkdown text={result.justificacion} />
      </div>

      <div className="method-selector">
        <div>
          <span>Decision final</span>
          <strong>Elige el metodo que se usara en la estimacion</strong>
          <p>Puedes conservar la recomendacion del agente o seleccionar manualmente otra alternativa disponible.</p>
        </div>
        <label>
          <span>Metodo de estimacion causal</span>
          <select className="select-field" value={selectedMethod} onChange={(event) => setSelectedMethod(event.target.value)}>
            {causalEstimationMethods.map((method) => (
              <option key={method} value={method}>
                {method}
              </option>
            ))}
          </select>
        </label>
        <div className={`method-selection-note ${isRecommendedMethod ? "recommended" : "custom"}`}>
          {isRecommendedMethod
            ? "Estas usando el metodo recomendado por el agente."
            : "Has elegido un metodo alternativo. La estimacion y la robustez se recalcularan con esta opcion."}
        </div>
      </div>
    </div>
  );
}

function ReadableAgentMarkdown({ text }: { text: string }) {
  const normalized = text
    .replace(/\r/g, "")
    .replace(/\\\s*\n/g, "\n")
    .replace(/###\s+(Resumen|Por que encaja|Por qué encaja|Cautela principal)\s*/g, "\n\n**$1:**\n")
    .replace(/\s+\*\*(Resumen|Diagnostico del dataset|Diagnóstico del dataset|Lectura practica|Lectura práctica):\*\*/g, "\n\n**$1:**")
    .replace(/\s+-\s+\*\*/g, "\n- **");
  const blocks = normalized
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  return (
    <div className="agent-markdown">
      {blocks.map((block, blockIndex) => {
        const lines = block
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean);
        const headingMatch = lines[0]?.match(/^\*\*(.+?):\*\*$/);
        const contentLines = headingMatch ? lines.slice(1) : lines;
        const listLines = contentLines.filter((line) => /^-\s+/.test(line));
        const paragraphLines = contentLines.filter((line) => !/^-\s+/.test(line));

        return (
          <section key={`${blockIndex}-${block.slice(0, 18)}`}>
            {headingMatch && <h5>{headingMatch[1]}</h5>}
            {paragraphLines.length > 0 && <p>{renderInlineMarkdown(paragraphLines.join(" "))}</p>}
            {listLines.length > 0 && (
              <ul>
                {listLines.map((line) => (
                  <li key={line}>{renderInlineMarkdown(line.replace(/^-\s+/, ""))}</li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}

function AgentInsightCards({ text }: { text: string }) {
  const sections = Array.from(
    text
      .replace(/\r/g, "")
      .trim()
      .matchAll(/(?:^|\n)\s*(\d+)\.\s+\*\*(.+?)\*\*\s*:?\s*([\s\S]*?)(?=(?:\n\s*)?\d+\.\s+\*\*|$)/g),
  ).map((match) => ({
    number: match[1],
    title: match[2].replace(/:$/, ""),
    body: match[3].trim(),
  }));

  if (!sections.length) {
    return <ReadableAgentMarkdown text={text} />;
  }

  return (
    <div className="agent-insight-grid">
      {sections.map((section) => (
        <article className="agent-insight-card" key={`${section.number}-${section.title}`}>
          <span>{section.number}</span>
          <div>
            <h5>{section.title}</h5>
            <p>{renderInlineMarkdown(section.body)}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function renderInlineMarkdown(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((chunk, index) =>
    chunk.startsWith("**") && chunk.endsWith("**") ? (
      <strong key={`${index}-${chunk}`}>{chunk.slice(2, -2)}</strong>
    ) : chunk.startsWith("`") && chunk.endsWith("`") ? (
      <code key={`${index}-${chunk}`}>{chunk.slice(1, -1)}</code>
    ) : (
      chunk
    ),
  );
}

function MethodList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "neutral" | "positive" | "warning";
}) {
  return (
    <div className={`method-list ${tone}`}>
      <strong>{title}</strong>
      <ul>
        {items.length ? items.map((item) => <li key={item}>{item}</li>) : <li>No hay avisos relevantes.</li>}
      </ul>
    </div>
  );
}

function DagDiagram({ dot, compact = false }: { dot: string; compact?: boolean }) {
  const graph = parseDotGraph(dot);

  if (!graph.nodes.length) {
    return <div className="dag-empty">No se pudo dibujar el DAG. Revisa el DOT generado.</div>;
  }

  const positions = layoutDagNodes(graph.nodes);
  const nodeByName = new Map(graph.nodes.map((node) => [node.name, node]));

  return (
    <div className={`dag-canvas ${compact ? "compact" : ""}`} aria-label="DAG causal generado">
      <svg viewBox="0 0 960 460" role="img">
        <defs>
          <marker id="dag-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#23314a" />
          </marker>
        </defs>
        {graph.edges.map((edge) => {
          const from = positions[edge.from];
          const to = positions[edge.to];
          if (!from || !to) {
            return null;
          }
          return (
            <line
              key={`${edge.from}-${edge.to}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#23314a"
              strokeWidth="2"
              markerEnd="url(#dag-arrow)"
            />
          );
        })}
        {graph.nodes.map((node) => {
          const position = positions[node.name];
          const style = dagNodeStyle(node);
          const width = Math.max(120, Math.min(230, node.name.length * 10 + 42));
          return (
            <g key={node.name} transform={`translate(${position.x}, ${position.y})`}>
              <rect
                x={-width / 2}
                y="-24"
                width={width}
                height="48"
                rx="24"
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth={style.strong ? 3 : 2}
              />
              <text textAnchor="middle" dominantBaseline="middle" fill="#101827" fontSize="15" fontWeight="800">
                {nodeByName.get(node.name)?.name}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="dag-legend">
        <span className="legend-item treatment">Treatment</span>
        <span className="legend-item outcome">Outcome</span>
        <span className="legend-item confounder">Confusoras</span>
        <span className="legend-item mediator">Relacionadas</span>
      </div>
    </div>
  );
}

type DagNode = {
  name: string;
  fill: string;
};

function parseDotGraph(dot: string): { nodes: DagNode[]; edges: Array<{ from: string; to: string }> } {
  const nodes = new Map<string, DagNode>();
  const edges: Array<{ from: string; to: string }> = [];
  const nodePattern = /"([^"]+)"\s*\[([^\]]*)\]/g;
  const edgePattern = /"([^"]+)"\s*->\s*"([^"]+)"/g;
  let nodeMatch: RegExpExecArray | null;
  let edgeMatch: RegExpExecArray | null;

  while ((nodeMatch = nodePattern.exec(dot))) {
    const fillMatch = /fillcolor="([^"]+)"/.exec(nodeMatch[2]);
    nodes.set(nodeMatch[1], { name: nodeMatch[1], fill: fillMatch?.[1] ?? "#E9EEF5" });
  }

  while ((edgeMatch = edgePattern.exec(dot))) {
    const from = edgeMatch[1];
    const to = edgeMatch[2];
    edges.push({ from, to });
    if (!nodes.has(from)) {
      nodes.set(from, { name: from, fill: "#E9EEF5" });
    }
    if (!nodes.has(to)) {
      nodes.set(to, { name: to, fill: "#E9EEF5" });
    }
  }

  return { nodes: Array.from(nodes.values()), edges };
}

function layoutDagNodes(nodes: DagNode[]) {
  const positions: Record<string, { x: number; y: number }> = {};
  const treatment = nodes.find((node) => node.name === "treatment");
  const outcome = nodes.find((node) => node.name !== "treatment" && isOutcomeNode(node));
  const confounders = nodes.filter((node) => node.fill.toLowerCase() === "#ffa500");
  const mediators = nodes.filter((node) => node.fill.toLowerCase() === "#b7e3ef");
  const others = nodes.filter(
    (node) => node !== treatment && node !== outcome && !confounders.includes(node) && !mediators.includes(node),
  );

  spreadNodes(confounders, 110, positions, 120, 840);
  spreadNodes(mediators, 280, positions, 190, 770);
  spreadNodes(others, 360, positions, 160, 800);

  if (treatment) {
    positions[treatment.name] = { x: 360, y: 185 };
  }
  if (outcome) {
    positions[outcome.name] = { x: 650, y: 380 };
  }

  nodes.forEach((node, index) => {
    if (!positions[node.name]) {
      positions[node.name] = { x: 160 + index * 120, y: 380 };
    }
  });

  return positions;
}

function spreadNodes(
  nodes: DagNode[],
  y: number,
  positions: Record<string, { x: number; y: number }>,
  minX: number,
  maxX: number,
) {
  if (!nodes.length) {
    return;
  }
  const step = nodes.length === 1 ? 0 : (maxX - minX) / (nodes.length - 1);
  nodes.forEach((node, index) => {
    positions[node.name] = { x: nodes.length === 1 ? (minX + maxX) / 2 : minX + step * index, y };
  });
}

function isOutcomeNode(node: DagNode) {
  const fill = node.fill.toLowerCase();
  return fill === "#d9d9d9" || fill === "lightgrey" || fill === "lightgray";
}

function dagNodeStyle(node: DagNode) {
  const fill = node.fill.toLowerCase();
  if (node.name === "treatment" || fill === "#b7f7b1") {
    return { fill: "#B7F7B1", stroke: "#2E7D32", strong: true };
  }
  if (isOutcomeNode(node)) {
    return { fill: "#D9D9D9", stroke: "#666666", strong: true };
  }
  if (fill === "#ffa500") {
    return { fill: "#FFA500", stroke: "#A65F00", strong: false };
  }
  if (fill === "#b7e3ef") {
    return { fill: "#B7E3EF", stroke: "#4F94A8", strong: false };
  }
  return { fill: "#E9EEF5", stroke: "#93A3B8", strong: false };
}

function formatMaybeNumber(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("es-ES", { maximumFractionDigits: 4 }) : "n/d";
}

function ChartsView({
  selectedDataset,
  profile,
}: {
  selectedDataset: string;
  profile: DatasetProfile | null;
}) {
  const [question, setQuestion] = useState("Haz un boxplot rosa del precio por carroceria");
  const [preferFallback, setPreferFallback] = useState(false);
  const [chartResult, setChartResult] = useState<ChartRenderResponse | null>(null);
  const [chartError, setChartError] = useState("");
  const [loadingChart, setLoadingChart] = useState(false);
  const chartExamples = buildChartExamples(profile);

  useEffect(() => {
    setChartResult(null);
    setChartError("");
  }, [selectedDataset]);

  async function submitChart() {
    const cleanQuestion = question.trim();
    if (!selectedDataset || !cleanQuestion || loadingChart) {
      return;
    }

    setLoadingChart(true);
    setChartError("");
    try {
      const result = await renderChart(selectedDataset, cleanQuestion, preferFallback);
      setChartResult(result);
    } catch (caughtError) {
      setChartError(caughtError instanceof Error ? caughtError.message : "No se pudo generar el grafico.");
      setChartResult(null);
    } finally {
      setLoadingChart(false);
    }
  }

  const imageSrc = chartResult
    ? `data:${chartResult.mime_type};base64,${chartResult.image_base64}`
    : "";

  function downloadChart() {
    if (!chartResult) {
      return;
    }

    const link = document.createElement("a");
    link.href = imageSrc;
    link.download = `wokia_grafico_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  return (
    <>
      <section className="page-intro charts-hero">
        <div>
          <p className="section-kicker">Graficos</p>
          <h3>Pide un grafico. Wokia lo construye.</h3>
          <p>
            Describe lo que quieres visualizar con tus palabras. Wokia genera el codigo Python, lo ejecuta sobre el
            dataset activo y devuelve una imagen lista para revisar o descargar.
          </p>
          <div className="charts-hero-tags">
            <span>Lenguaje natural</span>
            <span>Codigo Python generado</span>
            <span>Descarga PNG</span>
          </div>
        </div>
        <span className="dataset-name">{profile?.file_name ?? selectedDataset}</span>
      </section>

      <section className="chart-workbench vertical">
        <article className="panel chart-request-panel">
          <div className="panel-heading compact">
            <div>
              <p className="panel-kicker">Peticion</p>
              <h3>Describe el grafico</h3>
            </div>
            <BarChart3 size={20} className="muted" />
          </div>

          <label className="field-label" htmlFor="chart-question">
            Pregunta para el agente
          </label>
          <textarea
            id="chart-question"
            className="prompt-input"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={5}
            placeholder="Ej: Haz un histograma de PriceEuro"
          />

          <div className="suggestion-block">
            <span>Sugerencias segun el dataset</span>
            <div className="example-row" aria-label="Ejemplos de graficos">
              {chartExamples.map((example) => (
                <button className="example-chip" key={example} type="button" onClick={() => setQuestion(example)}>
                  {example}
                </button>
              ))}
            </div>
          </div>

          <label className="toggle-row">
            <input
              type="checkbox"
              checked={preferFallback}
              onChange={(event) => setPreferFallback(event.target.checked)}
            />
            <span>
              <strong>Modo rapido sin LLM</strong>
              <small>Usa plantillas deterministas cuando exista una coincidencia clara.</small>
            </span>
          </label>

          <button
            className="task-button primary"
            type="button"
            onClick={submitChart}
            disabled={!selectedDataset || !question.trim() || loadingChart}
          >
            {loadingChart ? (
              <>
                <Loader2 size={16} className="spin" />
                Generando
              </>
            ) : (
              "Generar grafico"
            )}
          </button>

          {chartError && <div className="task-error">{chartError}</div>}
        </article>

        <article className="panel chart-result-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Resultado</p>
              <h3>Grafico generado</h3>
            </div>
            <div className="result-actions">
              {chartResult && (
                <>
                  <div className="answer-meta">
                    <span>{chartResult.source === "llm" ? "LLM" : "Fallback"}</span>
                  </div>
                  <button className="secondary-button" type="button" onClick={downloadChart}>
                    Descargar PNG
                  </button>
                </>
              )}
            </div>
          </div>

          {chartResult ? (
            <>
              <div className="chart-image-frame">
                <img src={imageSrc} alt={`Grafico generado para: ${chartResult.question}`} />
              </div>

              <details className="code-disclosure">
                <summary>Ver codigo Python generado</summary>
                <pre>
                  <code>{chartResult.code}</code>
                </pre>
              </details>
            </>
          ) : (
            <div className="answer-placeholder chart-placeholder">
              <BarChart3 size={28} />
              <p>El grafico aparecera aqui cuando ejecutes una peticion.</p>
            </div>
          )}
        </article>
      </section>
    </>
  );
}

function ProfileView({
  selectedDataset,
  profile,
  loadingProfile,
}: {
  selectedDataset: string;
  profile: DatasetProfile | null;
  loadingProfile: boolean;
}) {
  const [summaryResults, setSummaryResults] = useState<Partial<Record<SummaryTask, AssistantSummaryResponse>>>({});
  const [summaryErrors, setSummaryErrors] = useState<Partial<Record<SummaryTask, string>>>({});
  const [loadingTask, setLoadingTask] = useState<SummaryTask | null>(null);
  const [selectedTask, setSelectedTask] = useState<SummaryTask>("structure");

  useEffect(() => {
    setSummaryResults({});
    setSummaryErrors({});
    setLoadingTask(null);
  }, [selectedDataset]);

  async function runSummaryTask(task: SummaryTask) {
    if (!selectedDataset || loadingTask) {
      return;
    }

    setLoadingTask(task);
    setSummaryErrors((current) => ({ ...current, [task]: undefined }));
    try {
      const result = await getAssistantSummary(selectedDataset, task);
      setSummaryResults((current) => ({ ...current, [task]: result }));
    } catch (caughtError) {
      setSummaryErrors((current) => ({
        ...current,
        [task]: caughtError instanceof Error ? caughtError.message : "No se pudo ejecutar esta tarea.",
      }));
    } finally {
      setLoadingTask(null);
    }
  }

  const activeTask = summaryTasks.find((task) => task.key === selectedTask) ?? summaryTasks[0];
  const ActiveIcon = activeTask.icon;
  const activeResult = summaryResults[selectedTask];
  const activeError = summaryErrors[selectedTask];
  const activeLoading = loadingTask === selectedTask;
  const previewColumns = profile?.preview[0]
    ? Object.keys(profile.preview[0])
    : profile?.columns.map((column) => column.name) ?? [];

  return (
    <>
      <section className="page-intro profile-hero">
        <div>
          <p className="section-kicker">Perfilado</p>
          <h3>Primer vistazo para conocer tus datos.</h3>
          <p>
            Mira una muestra real, entiende la estructura y lanza las lecturas del asistente solo cuando necesites
            profundizar.
          </p>
          <div className="profile-hero-tags">
            <span>Preview real</span>
            <span>8 tareas guiadas</span>
            <span>Sin gastar tokens hasta ejecutar</span>
          </div>
        </div>
        {loadingProfile && <Loader2 size={20} className="spin muted" />}
      </section>

      <section className="panel dataset-preview">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Vista previa</p>
            <h3>Primeras 10 filas</h3>
          </div>
          <span className="dataset-name">{profile?.file_name ?? selectedDataset}</span>
        </div>

        <div className="table-shell">
          <table>
            <thead>
              <tr>
                {previewColumns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(profile?.preview ?? []).map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {previewColumns.map((column) => (
                    <td key={column}>{formatCell(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="assistant-workbench">
        <aside className="task-sidebar panel">
          <div>
            <p className="panel-kicker">Tareas del asistente</p>
            <h3>Elige un analisis</h3>
          </div>

          <div className="task-list">
            {summaryTasks.map((task) => {
              const Icon = task.icon;

              return (
                <button
                  className={`task-list-item ${selectedTask === task.key ? "active" : ""}`}
                  key={task.key}
                  type="button"
                  onClick={() => setSelectedTask(task.key)}
                >
                  <div className="task-icon">
                    <Icon size={18} />
                  </div>
                  <span>
                    <strong>{task.title}</strong>
                    <small>{task.description}</small>
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        <article className="assistant-result panel">
          <div className="assistant-result-header">
            <div className="task-icon large">
              <ActiveIcon size={22} />
            </div>
            <div>
              <p className="panel-kicker">Resultado del asistente</p>
              <h3>{activeTask.title}</h3>
              <p>{activeTask.description}</p>
            </div>
          </div>

          <button
            className="task-button primary"
            type="button"
            onClick={() => runSummaryTask(selectedTask)}
            disabled={!selectedDataset || Boolean(loadingTask)}
          >
            {activeLoading ? (
              <>
                <Loader2 size={16} className="spin" />
                Analizando
              </>
            ) : activeResult ? (
              "Actualizar analisis"
            ) : (
              "Ejecutar analisis"
            )}
          </button>

          {activeResult ? (
            <div className="assistant-answer expanded">
              <div className="answer-meta">
                <span>{activeResult.mode === "llm" ? "LLM" : "Determinista"}</span>
              </div>
              <div className="profile-answer">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeResult.answer}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="answer-placeholder">
              <Brain size={24} />
              <p>Ejecuta esta tarea para ver aqui el analisis completo del dataset.</p>
            </div>
          )}

          {activeError && <div className="task-error">{activeError}</div>}
        </article>
      </section>
    </>
  );
}

function ComingSoonPanel({
  icon: Icon,
  title,
  copy,
}: {
  icon: typeof BarChart3;
  title: string;
  copy: string;
}) {
  return (
    <section className="empty-state">
      <div className="empty-icon">
        <Icon size={28} />
      </div>
      <h3>{title}</h3>
      <p>{copy}</p>
    </section>
  );
}

function MetricCard({
  label,
  value,
  helper,
  tone,
}: {
  label: string;
  value: string | number;
  helper: string;
  tone?: "ok" | "warn";
}) {
  return (
    <article className={`metric-card ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </article>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));
  }
  return String(value);
}

function buildChartExamples(profile: DatasetProfile | null): string[] {
  const numeric = profile?.numeric_columns ?? [];
  const categorical = profile?.categorical_columns ?? [];
  const firstNumeric = numeric[0];
  const secondNumeric = numeric[1];
  const firstCategorical = categorical[0];

  const examples: string[] = [];

  if (firstNumeric) {
    examples.push(`Haz un histograma de ${firstNumeric}`);
  }
  if (firstNumeric && firstCategorical) {
    examples.push(`Haz un boxplot de ${firstNumeric} por ${firstCategorical}`);
  }
  if (firstNumeric && secondNumeric) {
    examples.push(`Haz un grafico de dispersion de ${firstNumeric} en funcion de ${secondNumeric}`);
    examples.push("Haz un grafico de correlacion");
  }

  return examples.length
    ? examples.slice(0, 4)
    : [
        "Haz un histograma de una columna numerica",
        "Haz un grafico de barras de una columna categorica",
        "Haz un grafico de correlacion",
      ];
}
