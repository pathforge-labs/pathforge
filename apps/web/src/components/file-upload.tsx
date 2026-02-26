/**
 * PathForge — FileUpload Component
 * ==================================
 * Drag-and-drop + click-to-browse file upload with client-side validation.
 * Supports .txt files natively (read via FileReader) and shows guidance
 * for PDF/DOCX users to paste text instead.
 */

"use client";

import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/* ── Constants ────────────────────────────────────────────── */

const ACCEPTED_EXTENSIONS = [".txt", ".pdf", ".doc", ".docx"];
const ACCEPTED_MIME_TYPES = [
  "text/plain",
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const MAX_FILE_SIZE_LABEL = "5 MB";

/* ── Types ────────────────────────────────────────────────── */

export interface FileUploadProps {
  /** Called when a valid file is selected */
  readonly onFileSelect: (file: File) => void;
  /** Called when file is removed */
  readonly onFileRemove: () => void;
  /** Currently selected file, if any */
  readonly selectedFile: File | null;
  /** Whether the component is in a loading/processing state */
  readonly isLoading?: boolean;
  /** External error message to display */
  readonly error?: string | null;
}

/* ── Helpers ──────────────────────────────────────────────── */

function getFileExtension(fileName: string): string {
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex >= 0 ? fileName.slice(dotIndex).toLowerCase() : "";
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileTypeIcon(fileName: string): string {
  const extension = getFileExtension(fileName);
  switch (extension) {
    case ".pdf":
      return "📕";
    case ".doc":
    case ".docx":
      return "📘";
    case ".txt":
      return "📄";
    default:
      return "📎";
  }
}

function validateFile(file: File): string | null {
  const extension = getFileExtension(file.name);

  if (!ACCEPTED_EXTENSIONS.includes(extension) && !ACCEPTED_MIME_TYPES.includes(file.type)) {
    return `Unsupported file type "${extension || file.type}". Accepted: ${ACCEPTED_EXTENSIONS.join(", ")}`;
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large (${formatFileSize(file.size)}). Maximum size: ${MAX_FILE_SIZE_LABEL}.`;
  }

  if (file.size === 0) {
    return "File is empty. Please select a file with content.";
  }

  return null;
}

/* ── Component ────────────────────────────────────────────── */

export function FileUpload({
  onFileSelect,
  onFileRemove,
  selectedFile,
  isLoading = false,
  error: externalError,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const displayError = externalError ?? validationError;

  const handleFile = useCallback(
    (file: File) => {
      setValidationError(null);
      const errorMessage = validateFile(file);

      if (errorMessage) {
        setValidationError(errorMessage);
        return;
      }

      onFileSelect(file);
    },
    [onFileSelect],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragOver(false);

      const droppedFile = event.dataTransfer.files[0];
      if (droppedFile) {
        handleFile(droppedFile);
      }
    },
    [handleFile],
  );

  const handleInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const inputFile = event.target.files?.[0];
      if (inputFile) {
        handleFile(inputFile);
      }
      // Reset input so the same file can be re-selected
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [handleFile],
  );

  const handleBrowseClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleRemove = useCallback(() => {
    setValidationError(null);
    onFileRemove();
  }, [onFileRemove]);

  const isBinaryFile = selectedFile
    ? getFileExtension(selectedFile.name) !== ".txt"
    : false;

  return (
    <div className="space-y-3">
      {/* Drop zone (hidden when file selected) */}
      {!selectedFile && (
        <div
          data-testid="file-upload-dropzone"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleBrowseClick}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              handleBrowseClick();
            }
          }}
          className={`
            flex min-h-[200px] cursor-pointer flex-col items-center justify-center
            rounded-lg border-2 border-dashed p-6 text-center transition-all duration-200
            ${isDragOver
              ? "border-primary bg-primary/5 scale-[1.01]"
              : "border-border hover:border-primary/40 hover:bg-muted/30"
            }
            ${isLoading ? "pointer-events-none opacity-50" : ""}
          `}
        >
          <span className="mb-3 text-4xl">📁</span>
          <p className="text-sm font-medium">
            {isDragOver ? "Drop your file here" : "Drag & drop your resume here"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            or click to browse files
          </p>
          <p className="mt-3 text-xs text-muted-foreground">
            Supports {ACCEPTED_EXTENSIONS.join(", ")} • Max {MAX_FILE_SIZE_LABEL}
          </p>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={handleInputChange}
        className="hidden"
        data-testid="file-upload-input"
        aria-label="Upload resume file"
      />

      {/* File preview */}
      {selectedFile && (
        <Card className="border-primary/20">
          <CardContent className="flex items-center gap-3 py-4">
            <span className="text-2xl">{getFileTypeIcon(selectedFile.name)}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRemove}
              disabled={isLoading}
              data-testid="file-upload-remove"
            >
              Remove
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Binary file guidance */}
      {isBinaryFile && (
        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-600 dark:text-yellow-400">
          <p className="font-medium">PDF/DOCX detected</p>
          <p className="mt-1 text-xs">
            Server-side document parsing is coming soon. For now, please paste your
            resume text using the text input below.
          </p>
        </div>
      )}

      {/* Error display */}
      {displayError && (
        <div
          className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500"
          data-testid="file-upload-error"
          role="alert"
        >
          {displayError}
        </div>
      )}
    </div>
  );
}
