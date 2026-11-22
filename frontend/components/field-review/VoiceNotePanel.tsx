"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";

type Transcript = {
  transcript: string;
  language_code: string | null;
  language_probability: number | null;
  request_id: string | null;
  model: string | null;
};

const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const RECORDING_FORMATS = [
  { mime: "audio/webm;codecs=opus", extension: "webm" },
  { mime: "audio/ogg;codecs=opus", extension: "ogg" },
  { mime: "audio/mp4", extension: "m4a" },
] as const;

function extensionForType(type: string): string {
  if (type.includes("webm")) return "webm";
  if (type.includes("ogg")) return "ogg";
  if (type.includes("mp4")) return "m4a";
  return "audio";
}

export function VoiceNotePanel({ isAuthenticated }: { isAuthenticated: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const recordingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (recordingTimerRef.current) clearTimeout(recordingTimerRef.current);
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  const startRecording = async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Audio recording is not supported in this browser. Upload a clip instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const selected = RECORDING_FORMATS.find(({ mime }) => MediaRecorder.isTypeSupported(mime));
      const recorder = selected
        ? new MediaRecorder(stream, { mimeType: selected.mime })
        : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        if (recordingTimerRef.current) clearTimeout(recordingTimerRef.current);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "" });
        const extension = extensionForType(blob.type);
        setFile(new File([blob], `field-note.${extension}`, { type: blob.type }));
        setTranscript(null);
        setConfirmed(false);
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      recordingTimerRef.current = setTimeout(() => {
        if (recorder.state !== "inactive") {
          recorder.stop();
          setError("Recording stopped at the 30-second clip limit.");
        }
      }, 30_000);
    } catch {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setError("Microphone access was not available. You can upload an audio clip instead.");
    }
  };

  const stopRecording = () => recorderRef.current?.stop();

  const transcribe = async () => {
    if (!file || !isAuthenticated) return;
    setError("");
    setTranscript(null);
    setConfirmed(false);
    if (file.size === 0 || file.size > MAX_AUDIO_BYTES) {
      setError("Choose a non-empty audio clip no larger than 25 MB.");
      return;
    }
    const body = new FormData();
    body.append("audio", file, file.name);
    setBusy(true);
    try {
      const response = await fetch("/api/sarvam/transcribe", {
        method: "POST",
        body,
        credentials: "same-origin",
      });
      const result: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const message = typeof result === "object" && result !== null && "error" in result && typeof result.error === "string"
          ? result.error
          : "Transcription could not be completed.";
        throw new Error(message);
      }
      if (typeof result !== "object" || result === null || !("transcript" in result)) {
        throw new Error("Transcription returned an invalid response.");
      }
      const data = result as Record<string, unknown>;
      if (typeof data.transcript !== "string" || !data.transcript.trim()) throw new Error("Transcription returned an invalid response.");
      setTranscript({
        transcript: data.transcript,
        language_code: typeof data.language_code === "string" ? data.language_code : null,
        language_probability: typeof data.language_probability === "number" ? data.language_probability : null,
        request_id: typeof data.request_id === "string" ? data.request_id : null,
        model: typeof data.model === "string" ? data.model : null,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Transcription could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel rounded-2xl p-5 sm:p-6" aria-labelledby="voice-note-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="type-meta font-semibold uppercase tracking-[.08em] text-cyan-200/75">Field notes · Saaras v4</p>
          <h3 id="voice-note-title" className="mt-1.5 font-semibold text-white">Voice note transcription</h3>
          <p className="mt-1 max-w-xl type-detail text-slate-300">Record up to 30 seconds or upload a short note, review the transcript, then confirm it for this session. Confirmation does not save it.</p>
        </div>
        <span className="rounded-full border border-amber-200/20 bg-amber-200/[.06] px-3 py-1.5 type-meta font-medium text-amber-100">Not saved to an investigation</span>
      </div>

      {!isAuthenticated && <p className="mt-4 rounded-lg border border-amber-200/15 bg-amber-200/[.04] p-3 type-detail text-amber-100">Sign in with an officer account to use the authenticated transcription service.</p>}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {recording ? (
          <button type="button" onClick={stopRecording} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-rose-300/25 bg-rose-400/[.08] px-3 type-meta font-medium text-rose-100">
            <span className="size-2 animate-pulse rounded-full bg-rose-300" /> Stop recording
          </button>
        ) : (
          <button type="button" disabled={!isAuthenticated || busy} onClick={startRecording} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-cyan-200/20 bg-cyan-300/[.06] px-3 type-meta font-medium text-cyan-50 disabled:opacity-45">
            <Icon name="menu" size={15} /> Record voice note
          </button>
        )}
        <label className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-white/10 bg-white/[.03] px-3 type-meta font-medium text-slate-200 hover:border-cyan-200/25">
          Upload audio
          <input
            type="file"
            className="sr-only"
            accept="audio/wav,audio/mpeg,audio/aac,audio/aiff,audio/ogg,audio/opus,audio/flac,audio/mp4,audio/amr,audio/webm,.wav,.mp3,.aac,.aiff,.aif,.ogg,.opus,.flac,.m4a,.mp4,.amr,.wma,.webm"
            disabled={!isAuthenticated || busy || recording}
            onChange={(event) => {
              const nextFile = event.target.files?.[0] ?? null;
              setFile(nextFile);
              setTranscript(null);
              setConfirmed(false);
              setError("");
            }}
          />
        </label>
        {file && <span className="max-w-full truncate type-meta text-slate-400">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</span>}
        <button type="button" disabled={!file || !isAuthenticated || busy || recording} onClick={transcribe} className="primary-link inline-flex min-h-10 items-center gap-2 rounded-lg px-4 type-meta font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45">
          {busy ? "Transcribing…" : "Transcribe clip"}<Icon name="arrow" size={14} />
        </button>
      </div>

      {busy && <p role="status" className="mt-4 rounded-lg border border-cyan-200/10 bg-cyan-200/[.035] p-3 type-detail text-cyan-100">Sending securely to the authenticated transcription service…</p>}
      {error && <p role="alert" className="mt-4 rounded-lg border border-red-300/20 bg-red-400/10 p-3 type-detail text-red-100">{error}</p>}

      {transcript && (
        <div className="mt-5 border-t border-white/[.08] pt-5">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <label htmlFor="editable-transcript" className="type-control font-medium text-slate-200">Editable transcript</label>
            <span className="type-meta text-slate-500">{transcript.language_code ?? "Language not reported"}{transcript.model ? ` · ${transcript.model}` : ""}</span>
          </div>
          <textarea
            id="editable-transcript"
            rows={4}
            value={transcript.transcript}
            onChange={(event) => {
              setTranscript({ ...transcript, transcript: event.target.value });
              setConfirmed(false);
            }}
            className="w-full resize-y rounded-xl border border-cyan-200/15 bg-slate-950/45 p-3 text-sm leading-6 text-slate-100 outline-none focus:border-cyan-200/40"
          />
          {transcript.language_probability !== null && <p className="mt-2 type-meta text-slate-500">Language confidence: {(transcript.language_probability * 100).toFixed(1)}%</p>}
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button type="button" disabled={!transcript.transcript.trim()} onClick={() => setConfirmed(true)} className="min-h-9 rounded-lg border border-emerald-200/20 bg-emerald-300/[.06] px-3 type-meta font-medium text-emerald-100 disabled:opacity-50">Confirm transcript</button>
          {confirmed && <p role="status" className="type-detail text-emerald-100">Confirmed in this page only. It has not been saved.</p>}
          </div>
        </div>
      )}
    </section>
  );
}
