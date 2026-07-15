import { useCallback, useEffect, useRef, useState } from "react";
import { api, DocumentInfo } from "../lib/api";
import { FileIcon } from "../components/FileIcon";
import { UploadDocGlyph } from "../components/FileIcon";
import { EmptyState, PageHeader } from "../components/ui";
import { Chunking3D } from "../components/ThreeD";

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
          className={`focusable card border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200 ${
            dragging
              ? "border-ink bg-accent-soft scale-[1.01]"
              : "hover:border-ink-muted/40 hover:bg-hover"
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
          <div className="flex flex-col items-center gap-3">
            <UploadDocGlyph active={dragging} />
            <p className="text-sm">
              {dragging ? (
                <span className="text-ink font-medium">Drop to upload</span>
              ) : (
                <>
                  Drop files here or <span className="font-medium underline underline-offset-4">browse</span>
                </>
              )}
            </p>
            <div className="flex gap-2" aria-hidden>
              {["pdf", "docx", "pptx", "csv", "png"].map((type) => (
                <FileIcon key={type} type={type} size={18} />
              ))}
            </div>
          </div>
          <input
            ref={fileInput}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {error && <p className="text-signal text-sm anim-fade-up">{error}</p>}
        {Object.entries(uploads).map(([name, status]) => (
          <div key={name} className="card px-4 py-3 flex items-center gap-3 anim-fade-up">
            <FileIcon type={name} size={20} />
            <span className="text-sm flex-1 truncate">{name}</span>
            {status === "processing" ? (
              <span className="flex items-center gap-3">
                <Chunking3D size={26} />
                <span className="font-mono text-[11px] text-ink-muted">
                  chunking & indexing…
                </span>
              </span>
            ) : (
              <span
                className={`font-mono text-[12px] ${
                  status === "done" ? "text-verdigris" : "text-signal"
                }`}
              >
                {status === "done" ? "◉ indexed" : status}
              </span>
            )}
          </div>
        ))}

        {documents.length === 0 ? (
          <EmptyState title="No documents indexed yet — upload the first one above." />
        ) : (
          <div className="card overflow-x-auto anim-fade-up">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wider text-ink-muted border-b border-edge">
                  <th className="px-5 py-3">Document</th>
                  <th className="px-5 py-3">Version</th>
                  <th className="px-5 py-3">Chunks</th>
                  <th className="px-5 py-3">Entities</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.filename}
                    className="border-b border-edge last:border-0 hover:bg-hover transition-colors"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <FileIcon type={doc.filename} size={22} />
                        <div className="min-w-0">
                          <div className="truncate">{doc.title}</div>
                          <div className="font-mono text-[11px] text-ink-muted truncate">
                            {doc.filename} · {(doc.size_bytes / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono text-[12px]">v{doc.version}</td>
                    <td className="px-5 py-3 font-mono text-[12px]">{doc.chunks}</td>
                    <td className="px-5 py-3 font-mono text-[12px]">{doc.entities}</td>
                    <td className="px-5 py-3">
                      {doc.warnings.length === 0 ? (
                        <span className="text-verdigris font-mono text-[11px]">◉ indexed</span>
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
