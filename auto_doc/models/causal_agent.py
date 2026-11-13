# causal_agent.py
# Agent specifically designed for causal inference tasks with DoWhy tools.

from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
import re
import env_config
from auto_doc.causal.tools import (
    causal_tools,
    make_candidate_variables_tool,
    make_diagnostico_tool,
    make_python_repl_tool,
)

# LangChain imports
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, AgentType, AgentExecutor
from langchain.agents.mrkl.output_parser import MRKLOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


class LenientReActOutputParser(MRKLOutputParser):
    tool_names: list = []

    def __init__(self, tool_names):
        super().__init__(tool_names=list(tool_names))

    def parse(self, text):
        fixed_text = text
        for tool_name in self.tool_names:
            fixed_text = re.sub(
                rf"(?m)^Action\s*:\s*.*`?{re.escape(tool_name)}`?.*$",
                f"Action: {tool_name}",
                fixed_text,
            )
        return super().parse(fixed_text)

# -----------------------------
# Chat Model Loader
# -----------------------------
def get_causal_chat_model(temperature=0.0):
    if env_config.LLM_PROVIDER == "groq":
        return ChatGroq(
            model=env_config.GROQ_MODEL_NAME,
            api_key=env_config.GROQ_API_KEY,
            temperature=temperature
        )

    return ChatGoogleGenerativeAI(
        model=env_config.GEMINI_MODEL_NAME,
        api_key=env_config.GEMINI_API_KEY,
        temperature=temperature
    )

# -----------------------------
# Base Class
# -----------------------------
class BaseLLM(ABC):
    def __init__(self):
        self.chunk_size = 1
        self.temperature = 0.0

    @abstractmethod
    def load_llm_chat(self):
        pass

    @abstractmethod
    def run(self, prompt_text: str, params_dict: Optional[Dict[str, str]] = None) -> str:
        pass

# -----------------------------
# Concrete LLM Class
# -----------------------------
class CausalLLM(BaseLLM):
    def load_llm_chat(self):
        return get_causal_chat_model(temperature=self.temperature)

    def transform(self, llm, prompt_text: str, params_dict: Dict[str, str]) -> str:
        if not params_dict:
            result = llm.invoke(prompt_text)
            return getattr(result, "content", str(result))

        prompt = PromptTemplate(input_variables=list(params_dict.keys()), template=prompt_text)
        chain = prompt | llm
        result = chain.invoke(params_dict)
        return getattr(result, "content", str(result))

    def run(self, prompt_text: str, params_dict: Optional[Dict[str, str]] = None) -> str:
        llm = self.load_llm_chat()
        return self.transform(llm, prompt_text, params_dict or {})

# -----------------------------
# Custom Agent Executor
# -----------------------------
class CausalAgentExecutor:
    def __init__(self, agent: AgentExecutor):
        self.agent = agent

    def run(self, prompt: str) -> str:
        response = self.agent.run(prompt)
        if isinstance(response, str) and "Final Answer:" in response:
            return response.split("Final Answer:", 1)[1].strip()
        return response

# -----------------------------
# Causal Agent Factory
# -----------------------------
class CausalAgentFactory:
    def __init__(self):
        self.llm_instance = CausalLLM()
        self.llm = self.llm_instance.load_llm_chat()

    def create_agent(
        self,
        df: pd.DataFrame,
        verbose=True,
        allowed_tool_names: Optional[list] = None,
        max_iterations: int = 4,
    ) -> CausalAgentExecutor:

        df = df.reset_index(drop=True)

        memory = ConversationBufferMemory(memory_key="chat_history")

        python_tool = make_python_repl_tool(df)
        candidate_variables_tool = make_candidate_variables_tool(df)
        diagnostico_tool = make_diagnostico_tool(df)
        tools = causal_tools.copy() + [candidate_variables_tool, python_tool, diagnostico_tool]
        if allowed_tool_names is not None:
            allowed = set(allowed_tool_names)
            tools = [tool for tool in tools if tool.name in allowed]

        agent_prefix = """
Eres un asistente experto en ciencia de datos. Existe un DataFrame real de pandas ya cargado en la variable `df`.

Reglas obligatorias:
- Nunca digas que no tienes acceso al dataset.
- Nunca crees un DataFrame de ejemplo.
- Nunca sobrescribas `df`.
- Cuando necesites datos, usa la herramienta `python_repl_ast`.
- Para encontrar variables candidatas a partir de una pregunta causal, usa primero `find_candidate_variables`. No calcules correlaciones manualmente salvo que esa herramienta falle.
- Usa solo las herramientas disponibles para la fase actual. Si una herramienta no aparece en la lista, no la menciones ni la intentes llamar.
- En `Action Input` escribe solo codigo Python puro, sin backticks, sin Markdown y sin explicaciones.
- Si una herramienta devuelve error de formato, corrige el codigo y vuelve a intentarlo con Python puro.
- Si una accion devuelve `SyntaxError`, no repitas exactamente el mismo `Action Input`.
- Evita escribir bucles `for` completos en una sola linea. Prefiere expresiones simples como `list(df.columns)`, `df.dtypes`, `df.select_dtypes(include='number').columns.tolist()` o `next((col for col in df.columns if 'PriceEuro' in col), None)`.
- La respuesta final debe estar en espanol y basada solo en el contenido real de `df`.

Reglas internas de formato ReAct:
- Usa exactamente estas etiquetas en ingles: `Thought:`, `Action:`, `Action Input:`, `Observation:` y `Final Answer:`.
- No traduzcas las etiquetas internas. No uses `Observacion:` ni `Observación:`.
- En `Action:` escribe solo el nombre exacto de la herramienta. Ejemplo valido: `Action: python_repl_ast`. Ejemplo invalido: `Action: Utilizar python_repl_ast para consultar columnas`.
- Ejecuta solo una accion por turno.
- No inventes observaciones. Despues de `Action Input:` espera siempre a que la herramienta devuelva `Observation:`.
- No escribas `Final Answer:` en el mismo mensaje en el que escribes `Action:`.
- Nunca escribas `Action: None`. Si no necesitas mas acciones, escribe directamente `Final Answer:`.
- Cuando tengas suficiente informacion, escribe solo `Final Answer:` y ninguna accion.
- Si una herramienta devuelve un JSON completo, no lo ejecutes como otra accion. Devuelvelo directamente como `Final Answer:` usando comillas dobles validas.
"""

        base_agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=verbose,
            handle_parsing_errors=True,
            max_iterations=max_iterations,
            early_stopping_method="generate",
            memory=memory,
            agent_kwargs={
                "prefix": agent_prefix,
                "output_parser": LenientReActOutputParser([tool.name for tool in tools]),
            }
        )
        return CausalAgentExecutor(base_agent)
