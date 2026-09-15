import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { createHash } from "node:crypto";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const file = process.env.PI_BENCH_METRICS_FILE;
const now = () => process.hrtime.bigint().toString();
function emit(row: Record<string, unknown>) {
  if (!file) return;
  mkdirSync(dirname(file), { recursive: true });
  appendFileSync(file, JSON.stringify({ ...row, monotonicNs: now(), utc: new Date().toISOString() }) + "\n");
}

export default function (pi: ExtensionAPI) {
  let request = 0;
  let active = 0;
  const first = new Map<number, Set<string>>();
  pi.on("session_start", (_event, ctx) => emit({ event: "session_start", cwd: ctx.cwd, model: ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : null, thinking: ctx.thinkingLevel }));
  pi.on("agent_start", () => emit({ event: "agent_start" }));
  pi.on("agent_end", () => emit({ event: "agent_end" }));
  pi.on("turn_start", () => emit({ event: "turn_start" }));
  pi.on("turn_end", () => emit({ event: "turn_end" }));
  pi.on("before_provider_request", (event, ctx) => {
    active = ++request; first.set(active, new Set());
    const payload = JSON.stringify(event.payload);
    const p: any = event.payload;
    emit({ event: "provider_request", request: active, provider: ctx.model?.provider, model: ctx.model?.id, thinkingLevel: ctx.thinkingLevel, payloadBytes: Buffer.byteLength(payload), payloadSHA256: createHash("sha256").update(payload).digest("hex"), wireThinking: p.thinking ?? p.reasoning ?? null, wireReasoningEffort: p.reasoning_effort ?? p.reasoning?.effort ?? null });
  });
  pi.on("after_provider_response", (event) => emit({ event: "provider_response_headers", request: active, status: event.status, headers: event.headers }));
  pi.on("message_update", (event) => {
    const a: any = event.assistantMessageEvent; const seen = first.get(active) ?? new Set<string>(); first.set(active, seen);
    const kind = String(a.type ?? "unknown");
    const category = kind.startsWith("thinking_") ? "reasoning" : kind.startsWith("text_") || kind.startsWith("toolcall_") ? "action" : "other";
    if (!seen.has("any")) { seen.add("any"); emit({ event: "first_stream", request: active, category: "any", streamType: kind }); }
    if (!seen.has(category)) { seen.add(category); emit({ event: "first_stream", request: active, category, streamType: kind }); }
    if (kind.endsWith("_delta")) emit({ event: "stream_delta", request: active, category, streamType: kind, utf8Bytes: Buffer.byteLength(String(a.delta ?? "")), chars: Array.from(String(a.delta ?? "")).length });
  });
  pi.on("message_end", (event) => {
    if (event.message.role !== "assistant") return;
    const m: any = event.message;
    emit({ event: "assistant_end", request: active, stopReason: m.stopReason, usage: m.usage, contentBlocks: Array.isArray(m.content) ? m.content.length : null });
  });
  pi.on("tool_execution_start", (event) => emit({ event: "tool_start", request: active, toolCallId: event.toolCallId, toolName: event.toolName, argsSHA256: createHash("sha256").update(JSON.stringify(event.args)).digest("hex") }));
  pi.on("tool_execution_end", (event) => emit({ event: "tool_end", request: active, toolCallId: event.toolCallId, toolName: event.toolName, isError: event.isError }));
  pi.on("session_shutdown", () => emit({ event: "session_shutdown" }));
}
