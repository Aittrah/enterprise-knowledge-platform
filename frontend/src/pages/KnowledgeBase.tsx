import { useCallback, useEffect, useRef, useState } from "react";
import { api, DocumentInfo } from "../lib/api";
import { EmptyState, PageHeader } from "../components/ui";

export default function KnowledgeBase() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [uploads, setUploads] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    api.documents().then(setDocuments).catch(() => {});
  }, []);
  useEffect(refresh, [refresh]);

  async function handleFiles(files: FileList | null) {
    if (!files) return;
    setError("");
    for (const file of Array.from(files)) {
      try {
        const { job_id } = await api.upload(file);
        setUploads((u) => ({ ...u, [file.name]: "processing" }));
        pollJob(job_id, file.name);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      }
    }
  }

  function pollJob(jobId: string, filename: string) {
    const timer = setInterval(async () => {
      try {
        const job = await api.job(jobId);
        if (job.status === "completed" || job.status === "failed") {
          clearInterval(timer);
          setUploads((u) => ({
            ...u,
            [filename]: job.status === "completed" ? "done" : `failed: ${job.error}`,
          }));
          refresh();
        }
      } catch {
        clearInterval(timer);
      }
    }, 700);
  }

  return (
    <div className="pb-10">
      <PageHeader
        title="Knowledge Base"
        sub="Everything the agents can cite. Re-uploading a file supersedes its previous version."
      />
      <div className="px-8 space-y-5">
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload documents"
          className={`focusable card border-dashed p-10 text-center cursor-pointer transition-colors ${
            dragging ? "border-verdigris bg-verdigris/5" : "hover:border-white/20"
          }`}
          onClick={() => fileInput.current?.click()}
          onKeyDown={(e) => e.key === "Enter" && fileInput.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
        >
          <p className="text-sm">
            Drop files here or <span className="text-verdigris-bright">browse</span>
          </p>
          <p className="text-[12px] font-mono text-ink-muted mt-2">
            pdf · docx · txt · md · html · csv · pptx · png · jpg
          </p>
          <input
            ref={fileInput}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {error && <p className="text-signal text-sm">{error}</p>}
        {Object.entries(uploads).map(([name, status]) => (
          <div key={name} className="font-mono text-[12px] text-ink-muted">
            {name} —{" "}
            <span
              className={
                status === "done"
                  ? "text-verdigris-bright"
                  : status.startsWith("failed")
                    ? "text-signal"
                    : "text-marginalia"
              }
            >
              {status}
            </span>
          </div>
        ))}

        {documents.length === 0 ? (
          <EmptyState title="No documents indexed yet — upload the first one above." />
        ) : (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-ink-muted border-b border-white/8">
                  <th className="px-5 py-3">Document</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">Version</th>
                  <th className="px-5 py-3">Chunks</th>
                  <th className="px-5 py-3">Entities</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.filename} className="border-b border-white/4 last:border-0">
                    <td className="px-5 py-3">
                      <div>{doc.title}</div>
                      <div className="font-mono text-[11px] text-ink-muted">
                        {doc.filename} · {(doc.size_bytes / 1024).toFixed(1)} KB
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono text-[12px]">{doc.file_type}</td>
                    <td className="px-5 py-3 font-mono text-[12px]">v{doc.version}</td>
                    <td className="px-5 py-3 font-mono text-[12px]">{doc.chunks}</td>
                    <td className="px-5 py-3 font-mono text-[12px]">{doc.entities}</td>
                    <td className="px-5 py-3">
                      {doc.warnings.length === 0 ? (
                        <span className="text-verdigris-bright font-mono text-[11px]">
                          ◉ indexed
                        </span>
                      ) : (
                        <span
                          className="text-marginalia font-mono text-[11px]"
                          title={doc.warnings.join("\n")}
                        >
                          ◉ indexed · {doc.warnings.length} note(s)
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
