import {
  AppConfig,
  NoticeState,
  ProcessPayload,
} from "../../../../shared/models/readvideo-types/readvideo.types";

export interface ProcessingModelReadiness {
  validateWhisperSelection(): boolean;
  validateMlxSelection(): boolean;
  isInstalledOllamaModel(model: string): boolean;
  installedModels(): string[];
  whisperStatus(): NoticeState;
  mlxStatus(): NoticeState;
}

export interface ProcessingValidationFailure {
  message: string;
  logMessage: string;
}

export function processingValidationFailure(
  payload: ProcessPayload,
  config: AppConfig | null,
  models: ProcessingModelReadiness,
): ProcessingValidationFailure | null {
  if (payload.transcription_backend !== "openai" && !models.validateWhisperSelection()) {
    const message = models.whisperStatus().text;
    return {message, logMessage: message};
  }
  if (payload.notes_backend === "mlx") {
    if (models.validateMlxSelection()) return null;
    const message = models.mlxStatus().text;
    return {message, logMessage: message};
  }

  const selectedModel = payload.ollama_model || config?.ollama_model || "qwen3.6:35b";
  if (models.isInstalledOllamaModel(selectedModel)) return null;
  return {
    message: `缺少 Ollama 模型：${selectedModel}`,
    logMessage: `Ollama 当前可见模型：${models.installedModels().join(", ") || "无"}。缺少模型：${selectedModel}。`,
  };
}
